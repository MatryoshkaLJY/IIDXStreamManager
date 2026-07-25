"""比赛会话状态机：导播驱动的核心流程。

    IDLE → PREP（显示回合安排，导播分配机台+1P/2P 侧）
         → LIVE（确认开始，监控抓分）
         → REVIEW（收齐分数，自动判胜负，导播确认或改分）
         → PUSHED（已写入 scoreboard）
         → 下一回合 PREP / MATCH_END

会话本身不做任何 I/O（OBS、WebSocket），只产出状态与推送载荷，
I/O 由 app 层执行。分数服务的返回键是 `1pscore`/`2pscore`（无下划线）。
"""

from __future__ import annotations

import enum
from typing import Any

from ..config.models import KnockoutConfig, TeamMatchConfig
from .knockout import GROUP_SEQUENCE, ROUNDS_PER_GROUP, KnockoutTournament
from .scoring import judge_1v1, judge_2v2

SIDES = ("1p", "2p")


class SessionPhase(enum.Enum):
    IDLE = "IDLE"
    PREP = "PREP"
    LIVE = "LIVE"
    REVIEW = "REVIEW"
    PUSHED = "PUSHED"
    MATCH_END = "MATCH_END"


class SessionError(Exception):
    """非法的状态迁移或参数。"""


def parse_ex(machine_scores: dict[str, Any], side: str) -> int | None:
    """从分数服务返回的 dict 中取某侧 EX 分；取不到/非法返回 None。"""
    raw = machine_scores.get(f"{side}score")
    if raw is None:
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


class MatchSession:
    def __init__(self, mode: str, config: TeamMatchConfig | KnockoutConfig) -> None:
        if mode == "team":
            if not isinstance(config, TeamMatchConfig):
                raise SessionError("团队赛模式需要 TeamMatchConfig")
        elif mode == "knockout":
            if not isinstance(config, KnockoutConfig):
                raise SessionError("淘汰赛模式需要 KnockoutConfig")
        else:
            raise SessionError(f"未知模式: {mode!r}")
        self.mode = mode
        self.config = config
        self.phase = SessionPhase.IDLE
        # 团队赛进度
        self.round_index = 0
        self.team_round_results: list[dict[str, Any]] = []
        # 淘汰赛进度
        self.group_index = 0
        self.tournament: KnockoutTournament | None = None
        # 当前回合
        self.assignments: dict[str, dict[str, str]] = {}  # player -> {"machine", "side"}
        self.captured: dict[str, dict[str, Any]] = {}  # machine_id -> 分数服务返回
        self.last_result: dict[str, Any] | None = None
        self.last_payloads: list[dict[str, Any]] = []  # 最近一次 confirm 的推送载荷（重试用）

    # ---- 状态查询 ----

    @property
    def group(self) -> str:
        return GROUP_SEQUENCE[self.group_index]

    def players_to_assign(self) -> list[str]:
        """当前回合需要分配机台的选手。"""
        if self.mode == "team":
            rnd = self.config.rounds[self.round_index]  # type: ignore[union-attr]
            return rnd.all_players
        assert self.tournament is not None
        return self.tournament.active_players(self.group)

    def current_round_info(self) -> dict[str, Any]:
        """PREP/LIVE 页面展示用的当前回合信息。"""
        if self.mode == "team":
            cfg: TeamMatchConfig = self.config  # type: ignore[assignment]
            rnd = cfg.rounds[self.round_index]
            return {
                "mode": "team",
                "round_no": self.round_index + 1,
                "total_rounds": len(cfg.rounds),
                "type": rnd.type,
                "theme": rnd.theme,
                "points": rnd.points,
                "left_team": cfg.left_team.name,
                "right_team": cfg.right_team.name,
                "left_players": list(rnd.left_players),
                "right_players": list(rnd.right_players),
                "players": rnd.all_players,
            }
        assert self.tournament is not None
        group = self.group
        return {
            "mode": "knockout",
            "group": group,
            "stage": self.tournament.stage_of(group),
            "round_no": self.tournament.rounds_played[group] + 1,
            "total_rounds": ROUNDS_PER_GROUP,
            "tiebreaker": self.tournament.in_tiebreaker,
            "players": self.tournament.active_players(group),
            "lineup": self.tournament.lineup(group),
        }

    def snapshot(self) -> dict[str, Any]:
        """JSON 可序列化的状态快照（SocketIO 广播 / 持久化展示用）。"""
        info = (
            self.current_round_info()
            if self.phase in (SessionPhase.PREP, SessionPhase.LIVE, SessionPhase.REVIEW, SessionPhase.PUSHED)
            else None
        )
        summary: dict[str, Any] = {}
        if self.mode == "team":
            summary["team_rounds"] = self.team_round_results
        elif self.tournament is not None:
            summary["final_ranking"] = self.tournament.final_ranking
        return {
            "mode": self.mode,
            "phase": self.phase.value,
            "round": info,
            "assignments": self.assignments,
            "captured_machines": sorted(self.captured),
            "last_result": self.last_result,
            "summary": summary,
        }

    # ---- 流程 ----

    def start(self) -> None:
        if self.phase != SessionPhase.IDLE:
            raise SessionError(f"当前状态 {self.phase.value} 不能开始比赛")
        if self.mode == "knockout":
            cfg: KnockoutConfig = self.config  # type: ignore[assignment]
            self.tournament = KnockoutTournament(cfg.groups)
        self.round_index = 0
        self.group_index = 0
        self._enter_prep()

    def set_assignments(self, assignments: dict[str, dict[str, str]]) -> None:
        """导播为每个选手分配 {machine, side}。side ∈ {"1p","2p"}。"""
        if self.phase != SessionPhase.PREP:
            raise SessionError(f"当前状态 {self.phase.value} 不能分配机台")
        expected = set(self.players_to_assign())
        if set(assignments) != expected:
            raise SessionError(
                f"分配的选手集合不符：需要 {sorted(expected)}，实际 {sorted(assignments)}"
            )
        used: set[tuple[str, str]] = set()
        for player, slot in assignments.items():
            machine, side = slot.get("machine", ""), slot.get("side", "")
            if not machine or side not in SIDES:
                raise SessionError(f"选手 {player} 的机台/侧无效: {slot}")
            if (machine, side) in used:
                raise SessionError(f"机台 {machine} 的 {side} 侧被重复分配")
            used.add((machine, side))
        self.assignments = {p: {"machine": s["machine"], "side": s["side"]} for p, s in assignments.items()}

    def begin_round(self) -> None:
        if self.phase != SessionPhase.PREP:
            raise SessionError(f"当前状态 {self.phase.value} 不能开始回合")
        if set(self.assignments) != set(self.players_to_assign()):
            raise SessionError("尚未完成机台分配")
        self.captured = {}
        self.last_result = None
        self.phase = SessionPhase.LIVE

    def on_machine_scores(self, machine_id: str, scores: dict[str, Any]) -> bool:
        """LIVE 中收到某机台分数；收齐后自动进入 REVIEW。返回是否发生了迁移。"""
        if self.phase != SessionPhase.LIVE:
            return False
        self.captured[machine_id] = scores
        if self._all_captured():
            self.last_result = self._compute_result(self._player_scores())
            self.phase = SessionPhase.REVIEW
            return True
        return False

    def force_review(self, scores: dict[str, int]) -> None:
        """抓分失败时的应急通道：LIVE 中手动录入选手 EX 分直接进入 REVIEW。"""
        if self.phase != SessionPhase.LIVE:
            raise SessionError(f"当前状态 {self.phase.value} 不能手动录入")
        if set(scores) != set(self.players_to_assign()):
            raise SessionError("手动录入的选手集合与当前回合不符")
        self.last_result = self._compute_result({p: int(v) for p, v in scores.items()})
        self.phase = SessionPhase.REVIEW

    def review_info(self) -> dict[str, Any]:
        if self.phase not in (SessionPhase.REVIEW, SessionPhase.PUSHED):
            raise SessionError(f"当前状态 {self.phase.value} 没有可确认的分数")
        assert self.last_result is not None
        return self.last_result

    def confirm(self, final_scores: dict[str, int]) -> list[dict[str, Any]]:
        """导播确认（可改分）后计算结果并生成 scoreboard 推送载荷。

        `final_scores` 为本回合所有选手的最终 EX 分（{选手名: EX}）。
        返回按顺序发送的 payload 列表（score 在前，settle 在后）。
        """
        if self.phase != SessionPhase.REVIEW:
            raise SessionError(f"当前状态 {self.phase.value} 不能确认")
        expected = set(self.players_to_assign())
        if set(final_scores) != expected:
            raise SessionError(
                f"确认分数的选手集合不符：需要 {sorted(expected)}，实际 {sorted(final_scores)}"
            )
        scores = {p: int(v) for p, v in final_scores.items()}
        if self.mode == "team":
            payloads = self._confirm_team(scores)
        else:
            payloads = self._confirm_knockout(scores)
        self.last_payloads = payloads
        self.phase = SessionPhase.PUSHED
        return payloads

    def advance(self) -> None:
        """PUSHED → 下一回合 PREP 或 MATCH_END。"""
        if self.phase != SessionPhase.PUSHED:
            raise SessionError(f"当前状态 {self.phase.value} 不能进入下一回合")
        if self.mode == "team":
            self.round_index += 1
            if self.round_index >= len(self.config.rounds):  # type: ignore[union-attr]
                self.phase = SessionPhase.MATCH_END
                return
        else:
            assert self.tournament is not None
            if self.tournament.finished:
                self.phase = SessionPhase.MATCH_END
                return
            group = self.group
            if group != "finals" and self.tournament.group_complete(group):
                self.group_index += 1
            # finals 未结束（平局决胜）时停留在 finals 组
        self._enter_prep()

    def abort(self) -> None:
        """导播中止：回到 IDLE，清空进度。"""
        self.phase = SessionPhase.IDLE
        self.round_index = 0
        self.group_index = 0
        self.tournament = None
        self.assignments = {}
        self.captured = {}
        self.last_result = None
        self.team_round_results = []

    # ---- 内部 ----

    def _enter_prep(self) -> None:
        self.assignments = {}
        self.captured = {}
        self.last_result = None
        self.phase = SessionPhase.PREP

    def _all_captured(self) -> bool:
        for slot in self.assignments.values():
            scores = self.captured.get(slot["machine"])
            if scores is None or parse_ex(scores, slot["side"]) is None:
                return False
        return True

    def _player_scores(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for player, slot in self.assignments.items():
            ex = parse_ex(self.captured[slot["machine"]], slot["side"])
            assert ex is not None  # _all_captured 已保证
            result[player] = ex
        return result

    def _compute_result(self, scores: dict[str, int]) -> dict[str, Any]:
        """由选手 EX 分计算判定结果（REVIEW 展示 / 确认复算共用）。"""
        if self.mode == "team":
            rnd = self.config.rounds[self.round_index]  # type: ignore[union-attr]
            if rnd.type == "1v1":
                left_p, right_p = rnd.left_players[0], rnd.right_players[0]
                left_pts, right_pts = judge_1v1(scores[left_p], scores[right_p], rnd.points)
            else:
                side_scores = [("left", scores[p]) for p in rnd.left_players]
                side_scores += [("right", scores[p]) for p in rnd.right_players]
                left_pts, right_pts = judge_2v2(side_scores)
            return {
                "mode": "team",
                "scores": scores,
                "left_points": left_pts,
                "right_points": right_pts,
                "winner": (
                    "left" if left_pts > right_pts
                    else "right" if right_pts > left_pts
                    else "draw"
                ),
            }
        assert self.tournament is not None
        ranked = sorted(scores.items(), key=lambda item: -item[1])
        return {
            "mode": "knockout",
            "scores": scores,
            "ranking": [name for name, _ in ranked],
        }

    def _confirm_team(self, scores: dict[str, int]) -> list[dict[str, Any]]:
        result = self._compute_result(scores)
        self.last_result = result
        self.team_round_results.append(result)
        return [
            {
                "board": "bpl",
                "payload": {
                    "cmd": "score",
                    "data": {
                        "round": self.round_index + 1,
                        "leftScore": result["left_points"],
                        "rightScore": result["right_points"],
                    },
                },
            }
        ]

    def _confirm_knockout(self, scores: dict[str, int]) -> list[dict[str, Any]]:
        assert self.tournament is not None
        group = self.group
        stage = self.tournament.stage_of(group)
        round_no = self.tournament.rounds_played[group] + 1
        self.tournament.record_round(group, scores)
        self.last_result = self._compute_result(scores)

        payloads: list[dict[str, Any]] = [
            {
                "board": "knockout",
                "payload": {
                    "cmd": "score",
                    "data": {
                        "stage": stage,
                        "group": group,
                        "round": round_no,
                        "scores": [
                            {"player": name, "score": ex} for name, ex in scores.items()
                        ],
                    },
                },
            }
        ]
        if group == "finals":
            if self.tournament.group_complete(group) or self.tournament.in_tiebreaker:
                # 决赛不自动结算：第 4 局及每次加赛后都要显式 settle
                self.tournament.settle(group)
                payloads.append(
                    {
                        "board": "knockout",
                        "payload": {
                            "cmd": "settle",
                            "data": {"stage": "final", "group": "finals"},
                        },
                    }
                )
        elif self.tournament.group_complete(group):
            self.tournament.settle(group)  # A-F：board 端自动结算，管理端镜像推演
        return payloads

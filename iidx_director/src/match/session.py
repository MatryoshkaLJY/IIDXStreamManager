"""比赛会话状态机：导播驱动的核心流程。

    IDLE → PREP（显示回合安排，导播分配机台+1P/2P 侧）
         → LIVE（确认开始，监控抓分）
         → REVIEW（收齐分数，自动判胜负，导播确认或改分）
         → PUSHED（已写入 scoreboard）
         → 下一回合 PREP / MATCH_END

会话本身不做任何 I/O（OBS、WebSocket），只产出状态与推送载荷，
I/O 由 app 层执行。分数服务的返回键是 `1pscore`/`2pscore`（无下划线）；
BP 判定回合使用 `1pbp`/`2pbp`（miss count）。
"""

from __future__ import annotations

import enum
from typing import Any

from ..config.models import (
    KnockoutConfig,
    KnockoutEFConfig,
    KnockoutFinalConfig,
    TeamGame,
    TeamMatchConfig,
    TeamRound,
)
from .knockout import GROUP_SEQUENCE, ROUNDS_PER_GROUP, KnockoutTournament
from .scoring import judge_1v1, judge_1v1_bp, judge_2v2

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


def parse_bp(machine_scores: dict[str, Any], side: str) -> int | None:
    """从分数服务返回的 dict 中取某侧 BP（miss count）；取不到/非法返回 None。"""
    raw = machine_scores.get(f"{side}bp")
    if raw is None:
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


class MatchSession:
    def __init__(
        self, mode: str, config: TeamMatchConfig | KnockoutConfig | KnockoutEFConfig | KnockoutFinalConfig
    ) -> None:
        if mode == "team":
            if not isinstance(config, TeamMatchConfig):
                raise SessionError("团队赛模式需要 TeamMatchConfig")
        elif mode == "knockout":
            if not isinstance(config, KnockoutConfig):
                raise SessionError("淘汰赛模式需要 KnockoutConfig")
        elif mode == "knockout_ef":
            if not isinstance(config, KnockoutEFConfig):
                raise SessionError("EF 淘汰赛模式需要 KnockoutEFConfig")
        elif mode == "knockout_final":
            if not isinstance(config, KnockoutFinalConfig):
                raise SessionError("决赛模式需要 KnockoutFinalConfig")
        else:
            raise SessionError(f"未知模式: {mode!r}")
        self.mode = mode
        self.config = config
        self.phase = SessionPhase.IDLE
        # 团队赛进度
        self.round_index = 0
        self.team_round_results: list[dict[str, Any]] = []
        self.tiebreaker_rounds: list[TeamRound] = []  # 动态生成的加赛回合
        self.initial_scores: dict[str, int] | None = None  # 抢夺赛后导播录入的初始 PT
        # 淘汰赛进度
        self.group_index = 0
        self.tournament: KnockoutTournament | None = None
        # 当前回合
        self.assignments: dict[str, dict[str, str]] = {}  # player -> {"machine", "side"}
        self.captured: dict[str, dict[str, Any]] = {}  # machine_id -> 分数服务返回
        self.last_result: dict[str, Any] | None = None
        self.last_payloads: list[dict[str, Any]] = []  # 最近一次 confirm 的推送载荷（重试用）
        # 最近一次 confirm 是否为"局间静默推送"（淘汰赛局间不切计分板场景，仅同步数据）
        self.last_silent: bool = False
        self.game_index: int = 0  # 当前回合内的局索引（0/1；加赛为 0）
        self.game_results: list[dict[str, Any]] = []  # 当前回合已结束局的判定结果

    # ---- 状态查询 ----

    @property
    def is_knockout(self) -> bool:
        """是否为淘汰赛类模式（16 人赛 / 8 人 EF 赛制 / 4 人决赛赛制）。"""
        return self.mode in ("knockout", "knockout_ef", "knockout_final")

    @property
    def play_type(self) -> str:
        """当前赛程的游玩类型；旧配置缺省为 SP。"""
        return self.config.play_type

    @property
    def group(self) -> str:
        sequence = self.tournament.group_sequence if self.tournament else GROUP_SEQUENCE
        return sequence[self.group_index]

    def _current_team_round(self) -> TeamRound:
        """返回当前团队赛回合（常规或加赛），需要时惰性生成加赛回合。"""
        cfg: TeamMatchConfig = self.config  # type: ignore[assignment]
        if self.round_index < len(cfg.rounds):
            return cfg.rounds[self.round_index]
        tie_idx = self.round_index - len(cfg.rounds)
        while tie_idx >= len(self.tiebreaker_rounds):
            self._append_tiebreaker()
        return self.tiebreaker_rounds[tie_idx]

    def _append_tiebreaker(self) -> None:
        """生成一局 1v1 加赛回合。"""
        cfg: TeamMatchConfig = self.config  # type: ignore[assignment]
        left_player = cfg.left_team.players[0] if cfg.left_team.players else "左队选手"
        right_player = cfg.right_team.players[0] if cfg.right_team.players else "右队选手"
        game = TeamGame(
            theme="TIE BREAKER",
            left_players=[left_player],
            right_players=[right_player],
        )
        self.tiebreaker_rounds.append(TeamRound(type="1v1", games=[game], points=1))

    def _is_grab_round(self) -> bool:
        """当前回合是否为抢夺赛回合（不上计分板）。"""
        if self.mode != "team":
            return False
        cfg: TeamMatchConfig = self.config  # type: ignore[assignment]
        return self.round_index < cfg.grab_rounds

    def players_to_assign(self) -> list[str]:
        """当前回合需要分配机台的选手。"""
        if self.mode == "team":
            rnd = self._current_team_round()
            game = rnd.games[self.game_index]
            return [*game.left_players, *game.right_players]
        assert self.tournament is not None
        return self.tournament.active_players(self.group)

    def current_round_info(self) -> dict[str, Any]:
        """PREP/LIVE 页面展示用的当前回合信息。"""
        if self.mode == "team":
            cfg: TeamMatchConfig = self.config  # type: ignore[assignment]
            rnd = self._current_team_round()
            game = rnd.games[self.game_index]
            return {
                "mode": "team",
                "play_type": cfg.play_type,
                "round_no": self.round_index + 1,
                "total_rounds": len(cfg.rounds) + len(self.tiebreaker_rounds),
                "game_no": self.game_index + 1,
                "total_games": len(rnd.games),
                "type": rnd.type,
                "theme": rnd.theme or game.theme,
                "points": rnd.points,
                "judge_by": rnd.judge_by,
                "left_team": cfg.left_team.name,
                "right_team": cfg.right_team.name,
                "left_players": list(game.left_players),
                "right_players": list(game.right_players),
                "players": list(set([*game.left_players, *game.right_players])),
                "tiebreaker": self.round_index >= len(cfg.rounds),
                "grab": self._is_grab_round(),
            }
        assert self.tournament is not None
        group = self.group
        return {
            "mode": "knockout",
            "play_type": self.config.play_type,
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
        grab_rounds = self.config.grab_rounds if self.mode == "team" else 0
        return {
            "mode": self.mode,
            "play_type": self.play_type,
            "phase": self.phase.value,
            "round": info,
            "assignments": self.assignments,
            "captured_machines": sorted(self.captured),
            "last_result": self.last_result,
            "last_silent": self.last_silent,
            "game_index": self.game_index,
            "game_results": [dict(r) for r in self.game_results],
            "grab_rounds": grab_rounds,
            "initial_scores": self.initial_scores,
            "summary": summary,
        }

    # ---- 流程 ----

    def start(self) -> None:
        if self.phase != SessionPhase.IDLE:
            raise SessionError(f"当前状态 {self.phase.value} 不能开始比赛")
        if self.is_knockout:
            cfg: KnockoutConfig | KnockoutEFConfig | KnockoutFinalConfig = self.config  # type: ignore[assignment]
            self.tournament = KnockoutTournament(cfg.groups)
        # 团队赛回合结构（抢夺赛 1 局 / 常规 2~3 局）由 pydantic 模型校验保证
        self.round_index = 0
        self.group_index = 0
        self.tiebreaker_rounds = []
        self.initial_scores = None
        self._enter_prep()

    def set_initial_scores(self, left: int, right: int) -> None:
        """抢夺赛结束后录入双方初始 PT（由奖励抽取决定，程序无法自动判定）。"""
        if self.mode != "team":
            raise SessionError("仅团队赛支持初始 PT")
        cfg: TeamMatchConfig = self.config  # type: ignore[assignment]
        if cfg.grab_rounds <= 0:
            raise SessionError("当前赛程没有抢夺赛回合")
        if self.phase == SessionPhase.IDLE:
            raise SessionError("比赛尚未开始")
        if len(self.team_round_results) > cfg.grab_rounds or (
            len(self.team_round_results) == cfg.grab_rounds
            and self.phase not in (SessionPhase.PREP, SessionPhase.PUSHED)
        ):
            raise SessionError("正赛已开始，不能再录入初始 PT")
        if self.initial_scores is not None:
            raise SessionError("初始 PT 已录入，如需修改请中止比赛后重新开始")
        if left < 0 or right < 0:
            raise SessionError("初始 PT 不能为负")
        self.initial_scores = {"left": int(left), "right": int(right)}

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
        """LIVE/REVIEW 中收到某机台分数；LIVE 收齐后自动进入 REVIEW。

        REVIEW 中只更新已抓成绩（供重新抓分刷新），迁移由 enter_review 负责。
        返回是否发生了迁移。
        """
        if self.phase not in (SessionPhase.LIVE, SessionPhase.REVIEW):
            return False
        self.captured[machine_id] = scores
        if self.phase == SessionPhase.LIVE and self._all_captured():
            self.last_result = self._compute_result(self._player_scores())
            self.phase = SessionPhase.REVIEW
            return True
        return False

    def force_review(self, scores: dict[str, int]) -> None:
        """抓分失败时的应急通道：LIVE 中手动录入选手成绩直接进入 REVIEW。

        BP 判定回合中录入 miss count，其余录入 EX 分。
        """
        if self.phase != SessionPhase.LIVE:
            raise SessionError(f"当前状态 {self.phase.value} 不能手动录入")
        if set(scores) != set(self.players_to_assign()):
            raise SessionError("手动录入的选手集合与当前回合不符")
        self.last_result = self._compute_result({p: int(v) for p, v in scores.items()})
        self.phase = SessionPhase.REVIEW

    def enter_review(self) -> list[str]:
        """抓分结束后进入（或刷新）REVIEW，无论成绩是否收齐。

        未识别到成绩的选手在结果 scores 中记为 None（REVIEW 页面对应输入框
        留空，导播补录后才能确认），并列入返回值与结果的 incomplete 字段；
        临时判定按 0 占位计算，仅供展示，确认时会按最终成绩复算。
        """
        if self.phase not in (SessionPhase.LIVE, SessionPhase.REVIEW):
            raise SessionError(f"当前状态 {self.phase.value} 不能进入比分确认")
        scores: dict[str, int] = {}
        missing: list[str] = []
        for player, slot in self.assignments.items():
            machine_scores = self.captured.get(slot["machine"]) or {}
            value = self._parse_score(machine_scores, slot["side"])
            if value is None:
                missing.append(player)
                value = 0  # 占位，仅用于临时判定
            scores[player] = value
        result = self._compute_result(scores)
        for player in missing:
            result["scores"][player] = None
        result["incomplete"] = missing
        self.last_result = result
        self.phase = SessionPhase.REVIEW
        return missing

    def review_info(self) -> dict[str, Any]:
        if self.phase not in (SessionPhase.REVIEW, SessionPhase.PUSHED):
            raise SessionError(f"当前状态 {self.phase.value} 没有可确认的分数")
        assert self.last_result is not None
        return self.last_result

    def confirm(self, final_scores: dict[str, int]) -> list[dict[str, Any]]:
        """导播确认（可改分）后计算结果并生成 scoreboard 推送载荷。

        `final_scores` 为本回合所有选手的最终成绩（{选手名: 成绩}）；
        BP 判定回合中成绩为 miss count，其余为 EX 分。
        返回按顺序发送的 payload 列表（score 在前，settle 在后）。
        团队赛回合内还有下一局时返回空列表并回到 PREP；
        抢夺赛回合结束时也返回空列表，但进入 PUSHED（不上计分板）。
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
            payloads, round_complete = self._confirm_team(scores)
        else:
            payloads, round_complete = self._confirm_knockout(scores), True
        self.last_payloads = payloads
        if self.mode == "team" and not round_complete:
            # 团队赛当前回合还有下一局：保留机台分配，清空抓分状态，回到 PREP
            self._enter_prep(keep_assignments=True, reset_progress=False)
        else:
            self.phase = SessionPhase.PUSHED
        return payloads

    def advance(self) -> None:
        """PUSHED → 下一回合 PREP 或 MATCH_END。"""
        if self.phase != SessionPhase.PUSHED:
            raise SessionError(f"当前状态 {self.phase.value} 不能进入下一回合")

        keep_assignments = False
        if self.mode == "team":
            cfg: TeamMatchConfig = self.config  # type: ignore[assignment]
            base_rounds = len(cfg.rounds)
            left_total, right_total = self._team_totals()
            is_last_regular = self.round_index + 1 == base_rounds
            is_tiebreaker = self.round_index >= base_rounds

            # 最后一常规回合或加赛回合结束后若平局，进入加赛
            if (is_last_regular or is_tiebreaker) and left_total == right_total:
                self.round_index += 1
                self._current_team_round()  # 惰性生成加赛回合
                self._enter_prep()
                return

            self.round_index += 1
            if self.round_index >= base_rounds + len(self.tiebreaker_rounds):
                self.phase = SessionPhase.MATCH_END
                return
            keep_assignments = False  # 团队赛每回合都是新机台分配
        else:
            assert self.tournament is not None
            if self.tournament.finished:
                self.phase = SessionPhase.MATCH_END
                return
            old_group = self.group
            group = self.group
            if group != "finals" and self.tournament.group_settled(group):
                self.group_index += 1
            # 加赛未决出（含 finals）时停留在本组；
            # 即使同组，若 active players 变化（如加赛人数减少）也清空分配。
            same_group = self.group == old_group
            players_unchanged = set(self.assignments) == set(self.players_to_assign())
            keep_assignments = same_group and players_unchanged

        self._enter_prep(keep_assignments=keep_assignments)

    def abort(self) -> None:
        """导播中止：回到 IDLE，清空进度。"""
        self.phase = SessionPhase.IDLE
        self.round_index = 0
        self.group_index = 0
        self.tournament = None
        self.tiebreaker_rounds = []
        self.assignments = {}
        self.captured = {}
        self.last_result = None
        self.last_silent = False
        self.team_round_results = []
        self.initial_scores = None
        self.game_index = 0
        self.game_results = []

    # ---- 内部 ----

    def _team_totals(self) -> tuple[int, int]:
        """团队赛累计 PT。初始 PT 已录入时按计分板口径（初始 PT + 正赛回合合计）。"""
        if self.initial_scores is not None:
            scored = [r for r in self.team_round_results if not r.get("grab")]
            return (
                self.initial_scores["left"] + sum(r["left_points"] for r in scored),
                self.initial_scores["right"] + sum(r["right_points"] for r in scored),
            )
        return (
            sum(r["left_points"] for r in self.team_round_results),
            sum(r["right_points"] for r in self.team_round_results),
        )

    def _enter_prep(self, *, keep_assignments: bool = False, reset_progress: bool = True) -> None:
        if not keep_assignments:
            self.assignments = {}
        self.captured = {}
        self.last_result = None
        if reset_progress:
            self.game_index = 0
            self.game_results = []
        self.phase = SessionPhase.PREP

    def _current_judge_by(self) -> str:
        """当前回合的判定方式（"ex" / "bp"）；淘汰赛恒为 "ex"。"""
        if self.mode == "team":
            return self._current_team_round().judge_by
        return "ex"

    def _parse_score(self, machine_scores: dict[str, Any], side: str) -> int | None:
        """按当前回合判定方式取选手成绩：BP 回合取 miss count，其余取 EX 分。"""
        if self._current_judge_by() == "bp":
            return parse_bp(machine_scores, side)
        return parse_ex(machine_scores, side)

    def _all_captured(self) -> bool:
        for slot in self.assignments.values():
            scores = self.captured.get(slot["machine"])
            if scores is None or self._parse_score(scores, slot["side"]) is None:
                return False
        return True

    def _player_scores(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for player, slot in self.assignments.items():
            score = self._parse_score(self.captured[slot["machine"]], slot["side"])
            assert score is not None  # _all_captured 已保证
            result[player] = score
        return result

    def _compute_result(self, scores: dict[str, int]) -> dict[str, Any]:
        """由选手成绩计算判定结果（REVIEW 展示 / 确认复算共用）。

        `scores` 为 {选手: 成绩}；BP 判定回合中"成绩"为 miss count（少者胜），
        其余为 EX 分（高者胜）。
        """
        if self.mode == "team":
            rnd = self._current_team_round()
            game = rnd.games[self.game_index]
            if rnd.type == "1v1":
                left_p, right_p = game.left_players[0], game.right_players[0]
                if rnd.judge_by == "bp":
                    left_pts, right_pts = judge_1v1_bp(scores[left_p], scores[right_p], rnd.points)
                else:
                    left_pts, right_pts = judge_1v1(scores[left_p], scores[right_p], rnd.points)
            else:
                side_scores = [("left", scores[p]) for p in game.left_players]
                side_scores += [("right", scores[p]) for p in game.right_players]
                left_pts, right_pts = judge_2v2(side_scores)
            return {
                "mode": "team",
                "judge_by": rnd.judge_by,
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
            # 竞争排名：同分同名次（与 knockout.py 单局积分口径一致）
            "ranks": {
                name: 1 + sum(1 for v in scores.values() if v > ex)
                for name, ex in scores.items()
            },
        }

    def _confirm_team(self, scores: dict[str, int]) -> tuple[list[dict[str, Any]], bool]:
        """确认团队赛当前局结果。返回 (推送载荷, 本回合是否结束)。

        若当前回合还有下一局，则保存本局结果并回到 PREP（返回空载荷 + False）。
        抢夺赛回合结束时只记录结果、返回 (空载荷, True)，由 app 层跳过计分板。
        常规回合结束时合计所有局分数，返回 (score 载荷, True)。
        """
        result = self._compute_result(scores)
        self.last_result = result
        self.game_results.append(result)
        rnd = self._current_team_round()

        # 还有下一局：不清空 round 状态，返回空载荷让 confirm() 回到 PREP
        if self.game_index + 1 < len(rnd.games):
            self.game_index += 1
            return [], False

        # 当前回合结束：合计所有局分数
        left_total = sum(r["left_points"] for r in self.game_results)
        right_total = sum(r["right_points"] for r in self.game_results)
        round_result = {
            "mode": "team",
            "judge_by": rnd.judge_by,
            "scores": {p: s for r in self.game_results for p, s in r["scores"].items()},
            "left_points": left_total,
            "right_points": right_total,
            "winner": (
                "left" if left_total > right_total
                else "right" if right_total > left_total
                else "draw"
            ),
            "game_results": [dict(r) for r in self.game_results],
        }
        self.team_round_results.append(round_result)
        self.last_result = round_result
        self.game_results = []
        self.game_index = 0

        cfg: TeamMatchConfig = self.config  # type: ignore[assignment]
        if self._is_grab_round():
            # 抢夺赛回合：标记后不上计分板
            round_result["grab"] = True
            return [], True

        return [
            {
                "board": "bpl",
                "payload": {
                    "cmd": "score",
                    "data": {
                        "round": self.round_index + 1 - cfg.grab_rounds,
                        "leftScore": left_total,
                        "rightScore": right_total,
                    },
                },
            }
        ], True

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
            # A-F：board 端自动结算，管理端镜像推演；加赛期间每次 confirm 都重新结算
            self.tournament.settle(group)
        return payloads

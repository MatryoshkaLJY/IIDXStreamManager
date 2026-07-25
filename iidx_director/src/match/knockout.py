"""淘汰赛进程推演：复刻 iidx_knockout_scoreboard/app.js 的晋级与平局决胜逻辑。

管理端需要自己推演半决赛/决赛对阵（board 端只管显示），规则与 app.js 严格一致：
- A-F 组每组 4 局，单局排名 PT = 2/1/0/0；
- 组内结算按 PT 降序、并列按 totalRawScore 降序，前两名晋级；
- 晋级映射（app.js handleSettle）：
  A: 1st→E[0] 2nd→F[0]；B: 1st→F[1] 2nd→E[1]；
  C: 1st→F[2] 2nd→E[2]；D: 1st→E[3] 2nd→F[3]；
  E: 1st→finals[0] 2nd→finals[1]；F: 1st→finals[2] 2nd→finals[3]；
- 决赛 4 局后按 PT 分组：无并列直接定名次；有并列进入平局决胜，
  加赛成绩累计 tiebreakerScore，再次结算时各并列组内按 tiebreakerScore 定名次
  （board 端即使加赛再平分也会直接按排序定名次，不会无限加赛）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

POINTS_BY_RANK = (2, 1, 0, 0)
GROUP_SEQUENCE = ("A", "B", "C", "D", "E", "F", "finals")
ROUNDS_PER_GROUP = 4

STAGE_OF_GROUP = {
    "A": "quarterfinal",
    "B": "quarterfinal",
    "C": "quarterfinal",
    "D": "quarterfinal",
    "E": "semifinal",
    "F": "semifinal",
    "finals": "final",
}

# 1/4 决赛晋级映射：group -> (1st 目标组, 1st 位置, 2nd 目标组, 2nd 位置)
ADVANCE_QUARTER = {
    "A": ("E", 0, "F", 0),
    "B": ("F", 1, "E", 1),
    "C": ("F", 2, "E", 2),
    "D": ("E", 3, "F", 3),
}
# 半决赛晋级映射：group -> finals 起始位置（1st 占 offset，2nd 占 offset+1）
ADVANCE_SEMI_OFFSET = {"E": 0, "F": 2}


@dataclass
class PlayerStanding:
    name: str
    raw_scores: list[int | None] = field(default_factory=lambda: [None] * ROUNDS_PER_GROUP)
    points: int = 0
    total_raw: int = 0
    tiebreaker: int = 0


class KnockoutTournament:
    """镜像 board 端的淘汰赛状态。"""

    def __init__(self, groups: dict[str, list[str]]) -> None:
        self.groups: dict[str, list[PlayerStanding | None]] = {
            name: [PlayerStanding(p) for p in players]
            for name, players in groups.items()
            if name in ("A", "B", "C", "D")
        }
        for name in ("E", "F", "finals"):
            self.groups[name] = [None] * ROUNDS_PER_GROUP
        self.rounds_played: dict[str, int] = {name: 0 for name in GROUP_SEQUENCE}
        self.in_tiebreaker = False
        self.tie_groups: list[list[str]] = []  # 并列选手名（按 PT 分组）
        self.finished = False
        self.final_ranking: list[str] | None = None  # 决赛结算后的名次（含 🥇🥈🥉 顺序）

    # ---- 查询 ----

    def stage_of(self, group: str) -> str:
        return STAGE_OF_GROUP[group]

    def lineup(self, group: str) -> list[str]:
        """该组当前 4 名选手；E/F/finals 在晋级结算前可能有空位。"""
        names = [p.name if p else "" for p in self.groups[group]]
        return names

    def active_players(self, group: str) -> list[str]:
        """当前需要上机的选手：决赛平局决胜时只有并列选手继续。"""
        if group == "finals" and self.in_tiebreaker and self.tie_groups:
            tied = {name for tg in self.tie_groups for name in tg}
            return [p.name for p in self._standings("finals") if p.name in tied]
        return [n for n in self.lineup(group) if n]

    def group_complete(self, group: str) -> bool:
        return self.rounds_played[group] >= ROUNDS_PER_GROUP

    # ---- 记分 ----

    def record_round(self, group: str, scores: dict[str, int]) -> None:
        """记录当前组一局成绩。scores: {选手名: EX 分}。"""
        standings = {p.name: p for p in self._standings(group)}
        unknown = set(scores) - set(standings)
        if unknown:
            raise ValueError(f"组 {group} 中没有这些选手: {sorted(unknown)}")

        round_idx = min(self.rounds_played[group], ROUNDS_PER_GROUP - 1)
        ranked = sorted(scores.items(), key=lambda item: -item[1])  # 稳定排序
        if group == "finals" and self.in_tiebreaker:
            for name, ex in scores.items():
                standings[name].tiebreaker += ex
        else:
            for rank, (name, ex) in enumerate(ranked):
                player = standings[name]
                player.raw_scores[round_idx] = ex
                player.total_raw += ex
                player.points += POINTS_BY_RANK[rank]
        self.rounds_played[group] += 1

    # ---- 结算 ----

    def settle(self, group: str) -> None:
        """结算当前组。A-F：晋级两人；决赛：定名次或进入平局决胜。"""
        standings = self._standings(group)
        if group != "finals":
            if not self.group_complete(group):
                raise ValueError(f"组 {group} 未满 {ROUNDS_PER_GROUP} 局，不能结算")
            ranked = sorted(standings, key=lambda p: (-p.points, -p.total_raw))
            self._advance(group, ranked[0], ranked[1])
            return

        # 决赛
        if not self.in_tiebreaker:
            if not self.group_complete(group):
                raise ValueError("决赛未满 4 局，不能结算")
            ranked = sorted(standings, key=lambda p: -p.points)
            self.tie_groups = self._find_tie_groups(ranked)
            if self.tie_groups:
                self.in_tiebreaker = True
                return
            self.final_ranking = [p.name for p in ranked]
            self.finished = True
            return

        # 平局决胜结算：各并列组内按 tiebreaker 定名次（与 board 一致，平分也直接排）
        order: list[str] = []
        for tg in self.tie_groups:
            tied = [p for p in standings if p.name in tg]
            tied.sort(key=lambda p: -p.tiebreaker)
            order.extend(p.name for p in tied)
        ranked_names = [p.name for p in sorted(standings, key=lambda p: -p.points)]
        # 用加赛结果替换原排名中各并列组的位置
        result: list[str] = []
        tie_iter = iter(order)
        tie_names = {name for tg in self.tie_groups for name in tg}
        for name in ranked_names:
            result.append(next(tie_iter) if name in tie_names else name)
        self.final_ranking = result
        self.in_tiebreaker = False
        self.tie_groups = []
        self.finished = True

    # ---- 内部 ----

    def _standings(self, group: str) -> list[PlayerStanding]:
        players = [p for p in self.groups[group] if p is not None]
        if len(players) != ROUNDS_PER_GROUP:
            raise ValueError(f"组 {group} 对阵尚未确定（缺 {ROUNDS_PER_GROUP - len(players)} 人）")
        return players

    @staticmethod
    def _find_tie_groups(ranked: list[PlayerStanding]) -> list[list[str]]:
        groups: list[list[str]] = []
        i = 0
        while i < len(ranked):
            j = i + 1
            while j < len(ranked) and ranked[j].points == ranked[i].points:
                j += 1
            if j - i > 1:
                groups.append([p.name for p in ranked[i:j]])
            i = j
        return groups

    def _advance(self, group: str, first: PlayerStanding, second: PlayerStanding) -> None:
        if group in ADVANCE_QUARTER:
            g1, p1, g2, p2 = ADVANCE_QUARTER[group]
            self.groups[g1][p1] = PlayerStanding(first.name)
            self.groups[g2][p2] = PlayerStanding(second.name)
        else:
            offset = ADVANCE_SEMI_OFFSET[group]
            self.groups["finals"][offset] = PlayerStanding(first.name)
            self.groups["finals"][offset + 1] = PlayerStanding(second.name)

"""淘汰赛进程推演：复刻 iidx_knockout_scoreboard/app.js 的晋级与平局决胜逻辑。

管理端需要自己推演半决赛/决赛对阵（board 端只管显示），规则与 app.js 严格一致：
- A-F 组每组 4 局，单局名次采用竞争排名（同分同名次）：名次 = 1 + EX 严格更高的人数，
  单局 PT = 2/1/0/0，并列第一均得 2 PT、并列第二均得 1 PT；
- 组内结算按 PT 降序、PT 并列按 totalRawScore（4 局总 EX）降序，前两名晋级；
- PT 与总 EX 均相同的选手进入加赛：仅同分选手上机，EX 累计 tiebreaker，
  每次加赛后重新判定，仍并列的子组继续加赛直到分出胜负（可多次）；
- 非决赛组（A-F）只需决出前两名晋级：不跨越出线线（第 2/3 名之间）的并列不触发
  加赛——头名并列与第 3 名及以后的并列均按当前排序落位；加赛中一旦前两名归属已定，
  仍并列的子组也不再加赛，按加赛分顺序直接落位；
- 决赛按 PT 排名次，任何 PT 并列组都按上述加赛机制决出先后；
- 晋级映射（app.js handleSettle）：
  A: 1st→E[0] 2nd→F[0]；B: 1st→F[1] 2nd→E[1]；
  C: 1st→F[2] 2nd→E[2]；D: 1st→E[3] 2nd→F[3]；
  E: 1st→finals[0] 2nd→finals[1]；F: 1st→finals[2] 2nd→finals[3]。

支持三种赛制：16 人赛（初始组 A-D，1/4 决赛按 A→D→B→C 进行，随后 E→F→finals）、
8 人 EF 赛制（初始组 E/F，group_sequence 为 E→F→finals）与 4 人决赛赛制
（初始组 finals，group_sequence 仅 finals），后两者规则与 16 人赛的
半决赛/决赛完全一致，仅跳过前置阶段。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

POINTS_BY_RANK = (2, 1, 0, 0)
GROUP_SEQUENCE = ("A", "D", "B", "C", "E", "F", "finals")  # 16 人赛 1/4 决赛按 A→D→B→C 进行
GROUP_SEQUENCE_EF = ("E", "F", "finals")  # 8 人赛制（EF 组起）的组推进顺序
GROUP_SEQUENCE_FINAL = ("finals",)  # 4 人赛制（直接决赛）的组推进顺序
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
        # 配置中出现的 A-F/finals 组直接初始化为满员组（16 人赛为 A-D，8 人 EF 赛制
        # 为 E/F，4 人赛制为 finals），其余组保持空位，靠晋级结算填充。
        self.groups: dict[str, list[PlayerStanding | None]] = {}
        for name in ("A", "B", "C", "D", "E", "F", "finals"):
            players = groups.get(name)
            self.groups[name] = (
                [PlayerStanding(p) for p in players]
                if players is not None
                else [None] * ROUNDS_PER_GROUP
            )
        # 含任一 A-D 组按 16 人赛全流程推进；否则含 E/F 组为 8 人 EF 赛制
        # （E→F→决赛）；仅 finals 组为 4 人直接决赛赛制
        if any(name in groups for name in ("A", "B", "C", "D")):
            self.group_sequence: tuple[str, ...] = GROUP_SEQUENCE
        elif any(name in groups for name in ("E", "F")):
            self.group_sequence = GROUP_SEQUENCE_EF
        else:
            self.group_sequence = GROUP_SEQUENCE_FINAL
        self.rounds_played: dict[str, int] = {name: 0 for name in self.group_sequence}
        self.in_tiebreaker = False
        # 未决并列组：[(起始名次, 选手名列表)]，名次为对应排序口径下的 0 基下标
        self.tie_groups: list[tuple[int, list[str]]] = []
        self.settled_groups: set[str] = set()  # 已完成晋级的 A-F 组
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
        """当前需要上机的选手：加赛时只有仍未决出的并列选手继续。"""
        if self.in_tiebreaker and self.tie_groups:
            tied = {name for _, names in self.tie_groups for name in names}
            return [p.name for p in self._standings(group) if p.name in tied]
        return [n for n in self.lineup(group) if n]

    def group_complete(self, group: str) -> bool:
        return self.rounds_played[group] >= ROUNDS_PER_GROUP

    def group_settled(self, group: str) -> bool:
        """该组是否已彻底结算（A-F：已晋级；finals：已决出名次）。"""
        if group == "finals":
            return self.finished
        return group in self.settled_groups

    def should_show_scoreboard(self, group: str) -> bool:
        """一局 confirm 后是否应切计分板场景。

        局间（前 3 局、加赛未决期间）不切；一场 4 局结束（含因并列进入
        加赛前展示一次）或加赛决出后切换。
        """
        if self.group_settled(group):
            return True
        return self.in_tiebreaker and self.rounds_played[group] == ROUNDS_PER_GROUP

    # ---- 记分 ----

    def record_round(self, group: str, scores: dict[str, int]) -> None:
        """记录当前组一局成绩。scores: {选手名: EX 分}。"""
        standings = {p.name: p for p in self._standings(group)}
        unknown = set(scores) - set(standings)
        if unknown:
            raise ValueError(f"组 {group} 中没有这些选手: {sorted(unknown)}")

        if self.in_tiebreaker:
            # 加赛局：只累计加赛分，不影响常规局数据
            for name, ex in scores.items():
                standings[name].tiebreaker += ex
        else:
            round_idx = min(self.rounds_played[group], ROUNDS_PER_GROUP - 1)
            for name, ex in scores.items():
                # 竞争排名：同分同名次（并列第一均 2 PT、并列第二均 1 PT）
                rank = 1 + sum(1 for other in scores.values() if other > ex)
                player = standings[name]
                player.raw_scores[round_idx] = ex
                player.total_raw += ex
                player.points += POINTS_BY_RANK[rank - 1]
        self.rounds_played[group] += 1

    # ---- 结算 ----

    def settle(self, group: str) -> None:
        """结算当前组。A-F：晋级两人；决赛：定名次。存在并列时进入/推进加赛。"""
        standings = self._standings(group)
        if not self.in_tiebreaker:
            if not self.group_complete(group):
                raise ValueError(f"组 {group} 未满 {ROUNDS_PER_GROUP} 局，不能结算")
            if group == "finals":
                # 决赛只按 PT 排名，任何 PT 并列都加赛
                ranked = sorted(standings, key=lambda p: -p.points)
                self.tie_groups = self._find_tie_groups(ranked, key=lambda p: p.points)
            else:
                # A-F：PT 降序、并列按总 EX 降序；PT 与总 EX 均相同才加赛。
                # 只需决出前两名出线：不跨越出线线（第 2/3 名之间）的并列不加赛——
                # 头名并列（都出线）与第 3 名及以后的并列（都淘汰）均按当前排序落位
                ranked = sorted(standings, key=lambda p: (-p.points, -p.total_raw))
                self.tie_groups = [
                    (rank, names)
                    for rank, names in self._find_tie_groups(
                        ranked, key=lambda p: (p.points, p.total_raw)
                    )
                    if rank < 2 < rank + len(names)
                ]
            if self.tie_groups:
                self.in_tiebreaker = True
                return
            self._finish_group(group, [p.name for p in ranked])
            return

        # 加赛结算：各未决并列组内按 tiebreaker 定名次，仍平分的子组继续加赛
        placement: dict[int, str] = {}  # 已决出的 名次下标 -> 选手名
        pending: list[tuple[int, list[str]]] = []
        for start_rank, names in self.tie_groups:
            tied = [p for p in standings if p.name in names]
            tied.sort(key=lambda p: -p.tiebreaker)  # 稳定排序
            i = 0
            pos = start_rank
            while i < len(tied):
                j = i + 1
                while j < len(tied) and tied[j].tiebreaker == tied[i].tiebreaker:
                    j += 1
                sub = tied[i:j]
                if len(sub) > 1 and (group == "finals" or pos < 2 < pos + len(sub)):
                    pending.append((pos, [p.name for p in sub]))
                else:
                    # 单人直接落位；非决赛组不跨越出线线的并列按加赛分顺序落位，不再加赛
                    for k, p in enumerate(sub):
                        placement[pos + k] = p.name
                pos += len(sub)
                i = j
        if pending:
            # 仍有未决出的并列子组：继续加赛（已决出的选手不再上机）
            self.tie_groups = pending
            return

        # 全部决出：用加赛结果替换原排名中各并列区间的位置
        if group == "finals":
            ranked = sorted(standings, key=lambda p: -p.points)
        else:
            ranked = sorted(standings, key=lambda p: (-p.points, -p.total_raw))
        ordered = [placement.get(i, p.name) for i, p in enumerate(ranked)]
        self._finish_group(group, ordered)

    # ---- 内部 ----

    def _standings(self, group: str) -> list[PlayerStanding]:
        players = [p for p in self.groups[group] if p is not None]
        if len(players) != ROUNDS_PER_GROUP:
            raise ValueError(f"组 {group} 对阵尚未确定（缺 {ROUNDS_PER_GROUP - len(players)} 人）")
        return players

    @staticmethod
    def _find_tie_groups(
        ranked: list[PlayerStanding], key: Callable[[PlayerStanding], object]
    ) -> list[tuple[int, list[str]]]:
        """找出排序后 key 相同的相邻并列组，返回 [(起始名次下标, 选手名列表)]。"""
        groups: list[tuple[int, list[str]]] = []
        i = 0
        while i < len(ranked):
            j = i + 1
            while j < len(ranked) and key(ranked[j]) == key(ranked[i]):
                j += 1
            if j - i > 1:
                groups.append((i, [p.name for p in ranked[i:j]]))
            i = j
        return groups

    def _finish_group(self, group: str, ordered_names: list[str]) -> None:
        """组内名次全部决出：晋级或生成决赛名次，并退出加赛状态。"""
        if group == "finals":
            self.final_ranking = ordered_names
            self.finished = True
        else:
            self._advance(group, ordered_names[0], ordered_names[1])
            self.settled_groups.add(group)
        self.in_tiebreaker = False
        self.tie_groups = []

    def _advance(self, group: str, first_name: str, second_name: str) -> None:
        if group in ADVANCE_QUARTER:
            g1, p1, g2, p2 = ADVANCE_QUARTER[group]
            self.groups[g1][p1] = PlayerStanding(first_name)
            self.groups[g2][p2] = PlayerStanding(second_name)
        else:
            offset = ADVANCE_SEMI_OFFSET[group]
            self.groups["finals"][offset] = PlayerStanding(first_name)
            self.groups["finals"][offset + 1] = PlayerStanding(second_name)

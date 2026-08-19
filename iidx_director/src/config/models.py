"""赛程配置模型（pydantic v2）。

字段 alias 与两个 scoreboard 的 init 协议（camelCase）对齐，
`model_dump(by_alias=True)` 的结果可直接作为推送载荷的基础。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PLAYERS_PER_ROUND = {"1v1": 1, "2v2": 2}
KNOCKOUT_GROUPS = ("A", "B", "C", "D")
KNOCKOUT_EF_GROUPS = ("E", "F")
KNOCKOUT_GROUP_SIZE = 4


class TeamColors(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    primary: str = "#888888"
    secondary: str = "#ffffff"
    accent: str | None = None


class Team(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    emoji: str = ""
    colors: TeamColors = Field(default_factory=TeamColors)
    players: list[str] = Field(default_factory=list)  # 队员名单


class TeamGame(BaseModel):
    """团队赛单回合中的一局（一首歌）。"""

    model_config = ConfigDict(populate_by_name=True)

    theme: str = ""
    left_players: list[str] = Field(alias="leftPlayers")
    right_players: list[str] = Field(alias="rightPlayers")


class TeamRound(BaseModel):
    """团队赛单回合安排：正赛每回合两局（决赛末回合三局）共用回合主题；抢夺赛/加赛可为 1 局。"""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["1v1", "2v2"] = "1v1"
    theme: str = ""  # 回合主题（两局共用）；为空时回退到单局 theme
    games: list[TeamGame] = Field(default_factory=list)
    points: int = 1
    judge_by: Literal["ex", "bp"] = Field(default="ex", alias="judgeBy")  # 胜负判定：EX 分高者胜 / BP 少者胜

    @model_validator(mode="after")
    def _check_games(self) -> "TeamRound":
        # 常规回合为 2 局（决赛末回合可为 3 局）；抢夺赛/加赛回合可为 1 局
        # （按回合位置由 TeamMatchConfig 校验）。
        if len(self.games) not in (1, 2, 3):
            raise ValueError(f"团队赛每回合需要 1~3 局，实际 {len(self.games)} 局")
        if self.judge_by == "bp" and self.type != "1v1":
            raise ValueError("BP 判定仅支持 1v1 回合")
        expected = PLAYERS_PER_ROUND[self.type]
        for idx, game in enumerate(self.games, start=1):
            if len(game.left_players) != expected or len(game.right_players) != expected:
                raise ValueError(
                    f"第 {idx} 局每边需要 {expected} 名选手，"
                    f"实际左 {len(game.left_players)} / 右 {len(game.right_players)}"
                )
        if self.points < 0:
            raise ValueError("回合分值不能为负")
        return self

    @property
    def all_players(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for game in self.games:
            for p in [*game.left_players, *game.right_players]:
                if p not in seen:
                    seen.add(p)
                    result.append(p)
        return result


class TeamMatchConfig(BaseModel):
    """团队赛（BPL）整场比赛配置。"""

    model_config = ConfigDict(populate_by_name=True)

    play_type: Literal["SP", "DP"] = Field(default="SP", alias="playType")
    stage_name: str = Field(default="", alias="stageName")
    match_number: int = Field(default=1, alias="matchNumber")
    left_team: Team = Field(alias="leftTeam")
    right_team: Team = Field(alias="rightTeam")
    grab_rounds: int = Field(default=0, alias="grabRounds")  # 前 N 回合为抢夺赛（不上计分板）
    rounds: list[TeamRound]

    @model_validator(mode="after")
    def _check_rounds(self) -> "TeamMatchConfig":
        if not self.rounds:
            raise ValueError("至少需要一回合")
        if not 0 <= self.grab_rounds <= len(self.rounds):
            raise ValueError(f"grabRounds 需在 0~{len(self.rounds)} 之间，实际 {self.grab_rounds}")
        for idx, rnd in enumerate(self.rounds, start=1):
            if idx <= self.grab_rounds:
                # 抢夺赛：1v1 且只有 1 局（1 首歌）
                if rnd.type != "1v1" or len(rnd.games) != 1:
                    raise ValueError(f"第 {idx} 回合为抢夺赛，需要 1v1 且恰好 1 局")
            elif len(rnd.games) not in (2, 3):
                # 决赛最后一场为 3 首歌，其余常规回合 2 首
                raise ValueError(f"第 {idx} 常规回合需要 2 或 3 局，实际 {len(rnd.games)} 局")
        roster = set(self.left_team.players) | set(self.right_team.players)
        for idx, rnd in enumerate(self.rounds, start=1):
            unknown = [p for p in rnd.all_players if roster and p not in roster]
            if unknown:
                raise ValueError(f"第 {idx} 回合选手不在队员名单中: {unknown}")
        return self


class KnockoutConfig(BaseModel):
    """16 人个人淘汰赛配置：A-D 组各 4 人。"""

    model_config = ConfigDict(populate_by_name=True)

    play_type: Literal["SP", "DP"] = Field(default="SP", alias="playType")
    tournament_name: str = Field(default="16人淘汰赛", alias="tournamentName")
    groups: dict[str, list[str]]

    @model_validator(mode="after")
    def _check_groups(self) -> "KnockoutConfig":
        if set(self.groups) != set(KNOCKOUT_GROUPS):
            raise ValueError(f"分组必须是 {KNOCKOUT_GROUPS}，实际: {sorted(self.groups)}")
        seen: set[str] = set()
        for name, players in sorted(self.groups.items()):
            if len(players) != KNOCKOUT_GROUP_SIZE:
                raise ValueError(f"组 {name} 需要 {KNOCKOUT_GROUP_SIZE} 人，实际 {len(players)} 人")
            dup = seen.intersection(players)
            if dup:
                raise ValueError(f"选手重复出现在多个组: {sorted(dup)}")
            seen.update(players)
        return self


class KnockoutEFConfig(BaseModel):
    """8 人个人淘汰赛配置（EF 组起）：E/F 组各 4 人，各组前两名晋级 4 人决赛。

    规则与 16 人赛的 E/F 半决赛完全一致，仅没有 A-D 小组赛阶段。
    """

    model_config = ConfigDict(populate_by_name=True)

    play_type: Literal["SP", "DP"] = Field(default="SP", alias="playType")
    tournament_name: str = Field(default="8人淘汰赛", alias="tournamentName")
    groups: dict[str, list[str]]

    @model_validator(mode="after")
    def _check_groups(self) -> "KnockoutEFConfig":
        if set(self.groups) != set(KNOCKOUT_EF_GROUPS):
            raise ValueError(f"分组必须是 {KNOCKOUT_EF_GROUPS}，实际: {sorted(self.groups)}")
        seen: set[str] = set()
        for name, players in sorted(self.groups.items()):
            if len(players) != KNOCKOUT_GROUP_SIZE:
                raise ValueError(f"组 {name} 需要 {KNOCKOUT_GROUP_SIZE} 人，实际 {len(players)} 人")
            dup = seen.intersection(players)
            if dup:
                raise ValueError(f"选手重复出现在多个组: {sorted(dup)}")
            seen.update(players)
        return self


class KnockoutFinalConfig(BaseModel):
    """4 人决赛配置（直接决赛）：仅 finals 一组 4 人，打 4 局按 PT 定名次。

    规则与 16 人赛的决赛完全一致（任何 PT 并列都加赛）。
    """

    model_config = ConfigDict(populate_by_name=True)

    play_type: Literal["SP", "DP"] = Field(default="SP", alias="playType")
    tournament_name: str = Field(default="淘汰赛决赛", alias="tournamentName")
    groups: dict[str, list[str]]

    @model_validator(mode="after")
    def _check_groups(self) -> "KnockoutFinalConfig":
        if set(self.groups) != {"finals"}:
            raise ValueError(f"分组必须是 ('finals',)，实际: {sorted(self.groups)}")
        players = self.groups["finals"]
        if len(players) != KNOCKOUT_GROUP_SIZE:
            raise ValueError(f"决赛需要 {KNOCKOUT_GROUP_SIZE} 人，实际 {len(players)} 人")
        if len(set(players)) != len(players):
            raise ValueError("决赛选手名单存在重复")
        return self

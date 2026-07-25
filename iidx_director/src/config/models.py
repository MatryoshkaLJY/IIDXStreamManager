"""赛程配置模型（pydantic v2）。

字段 alias 与两个 scoreboard 的 init 协议（camelCase）对齐，
`model_dump(by_alias=True)` 的结果可直接作为推送载荷的基础。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PLAYERS_PER_ROUND = {"1v1": 1, "2v2": 2}
KNOCKOUT_GROUPS = ("A", "B", "C", "D")
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


class TeamRound(BaseModel):
    """团队赛单回合安排。"""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["1v1", "2v2"] = "1v1"
    theme: str = ""
    left_players: list[str] = Field(alias="leftPlayers")
    right_players: list[str] = Field(alias="rightPlayers")
    points: int = 1

    @model_validator(mode="after")
    def _check_player_counts(self) -> "TeamRound":
        expected = PLAYERS_PER_ROUND[self.type]
        if len(self.left_players) != expected or len(self.right_players) != expected:
            raise ValueError(
                f"{self.type} 回合每边需要 {expected} 名选手，"
                f"实际左 {len(self.left_players)} / 右 {len(self.right_players)}"
            )
        if self.points < 0:
            raise ValueError("回合分值不能为负")
        return self

    @property
    def all_players(self) -> list[str]:
        return [*self.left_players, *self.right_players]


class TeamMatchConfig(BaseModel):
    """团队赛（BPL）整场比赛配置。"""

    model_config = ConfigDict(populate_by_name=True)

    stage_name: str = Field(default="", alias="stageName")
    match_number: int = Field(default=1, alias="matchNumber")
    left_team: Team = Field(alias="leftTeam")
    right_team: Team = Field(alias="rightTeam")
    rounds: list[TeamRound]

    @model_validator(mode="after")
    def _check_rounds(self) -> "TeamMatchConfig":
        if not self.rounds:
            raise ValueError("至少需要一回合")
        roster = set(self.left_team.players) | set(self.right_team.players)
        for idx, rnd in enumerate(self.rounds, start=1):
            unknown = [p for p in rnd.all_players if roster and p not in roster]
            if unknown:
                raise ValueError(f"第 {idx} 回合选手不在队员名单中: {unknown}")
        return self


class KnockoutConfig(BaseModel):
    """16 人个人淘汰赛配置：A-D 组各 4 人。"""

    model_config = ConfigDict(populate_by_name=True)

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

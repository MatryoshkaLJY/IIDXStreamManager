from typing import Dict, List, Literal

from pydantic import BaseModel


class Player(BaseModel):
    id: str
    name: str
    role: str


class TeamColors(BaseModel):
    primary: str
    secondary: str
    accent: str


class Team(BaseModel):
    id: str
    name: str
    emoji: str
    colors: TeamColors
    players: List[Player]


class TeamsConfig(BaseModel):
    teams: List[Team]


class Round(BaseModel):
    type: Literal["1v1", "2v2"]
    theme: str
    left_players: List[str]
    right_players: List[str]


class Match(BaseModel):
    left_team: str
    right_team: str
    template: str
    rounds: List[Round]


class Week(BaseModel):
    matches: List[Match]


class TeamScheduleConfig(BaseModel):
    weeks: List[Week]


class IndividualScheduleConfig(BaseModel):
    groups: Dict[str, List[str]]


__all__ = [
    "Player",
    "TeamColors",
    "Team",
    "TeamsConfig",
    "Round",
    "Match",
    "Week",
    "TeamScheduleConfig",
    "IndividualScheduleConfig",
]

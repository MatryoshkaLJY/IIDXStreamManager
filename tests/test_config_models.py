import pytest
from pydantic import ValidationError

from src.config.models import (
    IndividualScheduleConfig,
    Round,
    TeamScheduleConfig,
    TeamsConfig,
)


def test_valid_teams_config():
    data = {
        "teams": [
            {
                "id": "team1",
                "name": "Team One",
                "emoji": "🦁",
                "colors": {
                    "primary": "#000000",
                    "secondary": "#FFFFFF",
                    "accent": "#FF0000",
                },
                "players": [
                    {"id": "p1", "name": "Player 1", "role": "attacker"}
                ],
            }
        ]
    }
    config = TeamsConfig.model_validate(data)
    assert len(config.teams) == 1
    assert config.teams[0].id == "team1"
    assert config.teams[0].players[0].role == "attacker"


def test_valid_team_schedule_config():
    data = {
        "weeks": [
            {
                "matches": [
                    {
                        "left_team": "team1",
                        "right_team": "team2",
                        "template": "standard",
                        "rounds": [
                            {
                                "type": "1v1",
                                "theme": "speed",
                                "left_players": ["p1"],
                                "right_players": ["p2"],
                            }
                        ],
                    }
                ]
            }
        ]
    }
    config = TeamScheduleConfig.model_validate(data)
    assert len(config.weeks) == 1
    assert config.weeks[0].matches[0].rounds[0].type == "1v1"


def test_valid_individual_schedule_config():
    data = {
        "groups": {
            "Group A": ["player1", "player2", "player3", "player4"],
            "Group B": ["player5", "player6", "player7", "player8"],
        }
    }
    config = IndividualScheduleConfig.model_validate(data)
    assert "Group A" in config.groups
    assert config.groups["Group A"] == ["player1", "player2", "player3", "player4"]


def test_invalid_round_type():
    data = {
        "type": "3v3",
        "theme": "speed",
        "left_players": ["p1"],
        "right_players": ["p2"],
    }
    with pytest.raises(ValidationError):
        Round.model_validate(data)


def test_empty_structures():
    assert TeamsConfig.model_validate({"teams": []}).teams == []
    assert TeamScheduleConfig.model_validate({"weeks": []}).weeks == []
    assert IndividualScheduleConfig.model_validate({"groups": {}}).groups == {}

import json

import pytest

from src.config.loader import ConfigError, ensure_templates, load_configs
from src.config.models import (
    IndividualScheduleConfig,
    TeamScheduleConfig,
    TeamsConfig,
)


def test_load_existing_valid_files(tmp_path):
    teams = {
        "teams": [
            {
                "id": "t1",
                "name": "Team 1",
                "emoji": "🦁",
                "colors": {"primary": "#000", "secondary": "#FFF", "accent": "#F00"},
                "players": [{"id": "p1", "name": "Player 1", "role": "atk"}],
            }
        ]
    }
    schedule = {
        "weeks": [
            {
                "matches": [
                    {
                        "left_team": "t1",
                        "right_team": "t2",
                        "template": "std",
                        "rounds": [
                            {
                                "type": "1v1",
                                "theme": "spd",
                                "left_players": ["p1"],
                                "right_players": ["p2"],
                            }
                        ],
                    }
                ]
            }
        ]
    }
    individual = {"groups": {"Group A": ["a1", "a2", "a3", "a4"]}}

    (tmp_path / "teams.json").write_text(json.dumps(teams), encoding="utf-8")
    (tmp_path / "team_schedule.json").write_text(json.dumps(schedule), encoding="utf-8")
    (tmp_path / "individual_schedule.json").write_text(
        json.dumps(individual), encoding="utf-8"
    )

    result = load_configs(tmp_path)
    assert isinstance(result["teams"], TeamsConfig)
    assert isinstance(result["team_schedule"], TeamScheduleConfig)
    assert isinstance(result["individual_schedule"], IndividualScheduleConfig)


def test_load_generates_missing_templates(tmp_path):
    result = load_configs(tmp_path)
    assert isinstance(result["teams"], TeamsConfig)
    assert isinstance(result["team_schedule"], TeamScheduleConfig)
    assert isinstance(result["individual_schedule"], IndividualScheduleConfig)
    assert (tmp_path / "teams.json").exists()
    assert (tmp_path / "team_schedule.json").exists()
    assert (tmp_path / "individual_schedule.json").exists()


def test_malformed_json_raises_config_error(tmp_path):
    (tmp_path / "teams.json").write_text("not json", encoding="utf-8")
    (tmp_path / "team_schedule.json").write_text("{}", encoding="utf-8")
    (tmp_path / "individual_schedule.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ConfigError) as exc_info:
        load_configs(tmp_path)
    assert "teams.json is not valid JSON" in str(exc_info.value)
    assert "Fix the file and reload the page to retry" in str(exc_info.value)


def test_schema_validation_raises_config_error(tmp_path):
    (tmp_path / "teams.json").write_text(
        json.dumps({"teams": [{"id": 123}]}), encoding="utf-8"
    )
    (tmp_path / "team_schedule.json").write_text(json.dumps({"weeks": []}), encoding="utf-8")
    (tmp_path / "individual_schedule.json").write_text(
        json.dumps({"groups": {}}), encoding="utf-8"
    )

    with pytest.raises(ConfigError) as exc_info:
        load_configs(tmp_path)
    assert "Config error: teams.json" in str(exc_info.value)
    assert "Fix the file and reload the page to retry" in str(exc_info.value)


def test_generated_templates_parse_successfully(tmp_path):
    ensure_templates(tmp_path)
    teams_raw = json.loads((tmp_path / "teams.json").read_text(encoding="utf-8"))
    schedule_raw = json.loads((tmp_path / "team_schedule.json").read_text(encoding="utf-8"))
    individual_raw = json.loads(
        (tmp_path / "individual_schedule.json").read_text(encoding="utf-8")
    )
    assert TeamsConfig.model_validate(teams_raw)
    assert TeamScheduleConfig.model_validate(schedule_raw)
    assert IndividualScheduleConfig.model_validate(individual_raw)

import json

import pytest

from src.config.loader import (
    ConfigError,
    ensure_templates,
    load_knockout,
    load_team_match,
    save_config,
)


def test_ensure_templates_and_load(tmp_path):
    ensure_templates(tmp_path)
    assert (tmp_path / "team_match.json").exists()
    assert (tmp_path / "knockout.json").exists()
    team = load_team_match(tmp_path)
    ko = load_knockout(tmp_path)
    assert team.rounds and ko.groups["A"]


def test_load_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="不存在"):
        load_team_match(tmp_path)


def test_load_invalid_json(tmp_path):
    (tmp_path / "team_match.json").write_text("{oops", encoding="utf-8")
    with pytest.raises(ConfigError, match="JSON"):
        load_team_match(tmp_path)


def test_load_validation_error(tmp_path):
    (tmp_path / "knockout.json").write_text(json.dumps({"groups": {"A": ["x"]}}), encoding="utf-8")
    with pytest.raises(ConfigError, match="校验失败"):
        load_knockout(tmp_path)


def test_save_config_validates_and_backs_up(tmp_path):
    ensure_templates(tmp_path)
    old = (tmp_path / "knockout.json").read_text(encoding="utf-8")
    payload = json.dumps(
        {
            "tournamentName": "测试杯",
            "groups": {g: [f"{g}{i}" for i in range(1, 5)] for g in "ABCD"},
        }
    )
    cfg = save_config("knockout.json", payload, tmp_path)
    assert cfg.tournament_name == "测试杯"
    assert (tmp_path / "knockout.json.bak").read_text(encoding="utf-8") == old
    assert load_knockout(tmp_path).tournament_name == "测试杯"


def test_save_config_rejects_invalid(tmp_path):
    ensure_templates(tmp_path)
    with pytest.raises(ConfigError, match="校验失败"):
        save_config("knockout.json", json.dumps({"groups": {}}), tmp_path)
    with pytest.raises(ConfigError, match="JSON"):
        save_config("knockout.json", "not json", tmp_path)
    with pytest.raises(ConfigError, match="未知"):
        save_config("evil.json", "{}", tmp_path)

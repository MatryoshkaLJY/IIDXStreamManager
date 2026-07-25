import pytest

from src.config.models import KnockoutConfig, TeamMatchConfig


def _team_match_dict():
    return {
        "stageName": "レギュラーステージ",
        "matchNumber": 3,
        "leftTeam": {
            "name": "SILK HAT",
            "emoji": "🎩",
            "colors": {"primary": "#c0c0c0", "secondary": "#ffffff"},
            "players": ["L1", "L2"],
        },
        "rightTeam": {
            "name": "ROCKET",
            "emoji": "🚀",
            "colors": {"primary": "#1a3a6b", "secondary": "#ffffff"},
            "players": ["R1", "R2"],
        },
        "rounds": [
            {"type": "1v1", "theme": "SCRATCH", "leftPlayers": ["L1"], "rightPlayers": ["R1"], "points": 1},
            {
                "type": "2v2",
                "theme": "CHARGE",
                "leftPlayers": ["L1", "L2"],
                "rightPlayers": ["R1", "R2"],
                "points": 2,
            },
        ],
    }


def _knockout_dict():
    return {
        "tournamentName": "16人淘汰赛",
        "groups": {g: [f"{g}{i}" for i in range(1, 5)] for g in "ABCD"},
    }


def test_team_match_valid():
    cfg = TeamMatchConfig.model_validate(_team_match_dict())
    assert cfg.stage_name == "レギュラーステージ"
    assert cfg.match_number == 3
    assert cfg.rounds[1].left_players == ["L1", "L2"]
    dumped = cfg.model_dump(by_alias=True)
    assert dumped["stageName"] == "レギュラーステージ"
    assert dumped["rounds"][0]["leftPlayers"] == ["L1"]


def test_team_match_round_player_count():
    raw = _team_match_dict()
    raw["rounds"][0]["leftPlayers"] = ["L1", "L2"]  # 1v1 只能 1 人
    with pytest.raises(Exception, match="1v1"):
        TeamMatchConfig.model_validate(raw)


def test_team_match_unknown_player():
    raw = _team_match_dict()
    raw["rounds"][0]["leftPlayers"] = ["GHOST"]
    with pytest.raises(Exception, match="不在队员名单"):
        TeamMatchConfig.model_validate(raw)


def test_team_match_empty_rounds():
    raw = _team_match_dict()
    raw["rounds"] = []
    with pytest.raises(Exception, match="至少需要一回合"):
        TeamMatchConfig.model_validate(raw)


def test_knockout_valid():
    cfg = KnockoutConfig.model_validate(_knockout_dict())
    assert cfg.groups["A"] == ["A1", "A2", "A3", "A4"]


def test_knockout_missing_group():
    raw = _knockout_dict()
    del raw["groups"]["D"]
    with pytest.raises(Exception, match="分组必须"):
        KnockoutConfig.model_validate(raw)


def test_knockout_group_size():
    raw = _knockout_dict()
    raw["groups"]["A"] = ["A1", "A2", "A3"]
    with pytest.raises(Exception, match="需要 4 人"):
        KnockoutConfig.model_validate(raw)


def test_knockout_duplicate_player():
    raw = _knockout_dict()
    raw["groups"]["B"][0] = "A1"
    with pytest.raises(Exception, match="重复"):
        KnockoutConfig.model_validate(raw)

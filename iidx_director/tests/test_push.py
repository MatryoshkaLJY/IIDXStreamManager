import json

import pytest

from src.config.models import KnockoutConfig, TeamMatchConfig
from src.match.session import MatchSession
from src.push.overlay import (
    OverlayPusher,
    hue_for_color,
    match_end_payload,
    round_start_payload,
    template_for_scene,
)
from src.push.scoreboard import (
    PushError,
    ScoreboardPusher,
    bpl_init_payload,
    bpl_reset_payload,
    knockout_init_payload,
    knockout_reset_payload,
)


def _team_config():
    return TeamMatchConfig.model_validate(
        {
            "stageName": "レギュラーステージ",
            "matchNumber": 12,
            "leftTeam": {
                "name": "SILK HAT",
                "emoji": "🎩",
                "colors": {"primary": "#c0c0c0", "secondary": "#ffffff"},
                "players": ["L1"],
            },
            "rightTeam": {
                "name": "ROCKET",
                "emoji": "🚀",
                "colors": {"primary": "#1a3a6b", "secondary": "#ffffff", "accent": "#ff0000"},
                "players": ["R1"],
            },
            "rounds": [
                {"type": "1v1", "theme": "SCRATCH", "leftPlayers": ["L1"], "rightPlayers": ["R1"], "points": 2}
            ],
        }
    )


# ---- 载荷构造 ----

def test_bpl_init_payload_matches_protocol():
    payload = bpl_init_payload(_team_config())
    assert payload["cmd"] == "init"
    data = payload["data"]
    assert data["stageName"] == "レギュラーステージ"
    assert data["matchNumber"] == 12
    assert data["leftTeam"] == {
        "name": "SILK HAT",
        "logo": "🎩",
        "colors": {"primary": "#c0c0c0", "secondary": "#ffffff"},
    }
    # accent 存在时透传
    assert data["rightTeam"]["colors"]["accent"] == "#ff0000"
    assert data["matches"] == [
        {"type": "1v1", "leftPlayers": ["L1"], "rightPlayers": ["R1"], "theme": "SCRATCH"}
    ]


def test_knockout_init_payload_matches_protocol():
    cfg = KnockoutConfig.model_validate(
        {"tournamentName": "杯赛", "groups": {g: [f"{g}{i}" for i in range(1, 5)] for g in "ABCD"}}
    )
    payload = knockout_init_payload(cfg)
    assert payload == {
        "cmd": "init",
        "data": {
            "tournamentName": "杯赛",
            "groups": {g: [f"{g}{i}" for i in range(1, 5)] for g in "ABCD"},
        },
    }


def test_reset_payloads():
    assert bpl_reset_payload() == {"cmd": "reset"}
    assert knockout_reset_payload() == {"cmd": "reset"}


# ---- 传输 ----

def test_push_sends_json(monkeypatch):
    sent = []

    class FakeWS:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def send(self, message):
            sent.append(message)

    monkeypatch.setattr("src.push.scoreboard.websockets.connect", lambda uri, open_timeout: FakeWS())
    pusher = ScoreboardPusher()
    pusher.push("bpl", {"cmd": "reset"})
    assert json.loads(sent[0]) == {"cmd": "reset"}


def test_push_unknown_board():
    with pytest.raises(PushError, match="未知记分板"):
        ScoreboardPusher().push("nope", {})


def test_push_connection_failure_raises():
    pusher = ScoreboardPusher(uris={"bpl": "ws://127.0.0.1:1"}, timeout=0.5)
    with pytest.raises(PushError, match="失败"):
        pusher.push("bpl", {"cmd": "reset"})


def test_push_all_stops_on_error(monkeypatch):
    calls = []

    def fake_push(board, payload):
        calls.append(board)
        if len(calls) == 2:
            raise PushError("boom")

    pusher = ScoreboardPusher()
    monkeypatch.setattr(pusher, "push", fake_push)
    items = [
        {"board": "knockout", "payload": {"cmd": "score"}},
        {"board": "knockout", "payload": {"cmd": "settle"}},
        {"board": "knockout", "payload": {"cmd": "reset"}},
    ]
    with pytest.raises(PushError):
        pusher.push_all(items)
    assert calls == ["knockout", "knockout"]


# ---- 场景信息 ----

def test_round_start_payload_team():
    session = MatchSession("team", _team_config())
    session.start()
    session.set_assignments(
        {"L1": {"machine": "IIDX#1", "side": "1p"}, "R1": {"machine": "IIDX#2", "side": "2p"}}
    )
    payload = round_start_payload(session)
    assert payload["cmd"] == "round_start"
    data = payload["data"]
    assert data["mode"] == "team"
    assert data["round"]["left_team"] == "SILK HAT"
    entries = {e["player"]: e for e in data["entries"]}
    assert entries["L1"] == {
        "player": "L1", "machine": "IIDX#1", "side": "1p",
        "team": "SILK HAT", "color": "#c0c0c0",
    }
    assert entries["R1"]["color"] == "#1a3a6b"


def test_overlay_template_and_text_fields():
    session = MatchSession("team", _team_config())
    session.start()
    session.set_assignments(
        {"L1": {"machine": "IIDX#1", "side": "1p"}, "R1": {"machine": "IIDX#2", "side": "2p"}}
    )
    payload = round_start_payload(session, "sp_bpl")
    assert payload["data"]["template"] == "sp_bpl"
    assert payload["data"]["texts"] == {
        "header_round": "ROUND 1",
        "header_theme": "SCRATCH",
        "left_team_name": "SILK HAT",
        "right_team_name": "ROCKET",
        "left_player": "L1",
        "right_player": "R1",
        "machine_1_player": "L1",
        "machine_2_player": "R1",
    }


def test_dp_default_scenes_select_dp_overlay_templates():
    cfg = TeamMatchConfig.model_validate(
        {
            "playType": "DP",
            "leftTeam": {"name": "L", "players": ["L1"]},
            "rightTeam": {"name": "R", "players": ["R1"]},
            "rounds": [{"type": "1v1", "leftPlayers": ["L1"], "rightPlayers": ["R1"]}],
        }
    )
    session = MatchSession("team", cfg)
    session.start()
    session.set_assignments(
        {"L1": {"machine": "IIDX#1", "side": "1p"}, "R1": {"machine": "IIDX#1", "side": "2p"}}
    )
    assert template_for_scene("DP_BPL", session.mode) == "dp_bpl"
    payload = round_start_payload(session, "dp_bpl", "DP_BPL")
    assert payload["data"]["template"] == "dp_bpl"


def test_template_for_scene():
    assert template_for_scene("DP团队赛", "team") == "dp_bpl"
    assert template_for_scene("SP团队赛", "team") == "sp_bpl"
    assert template_for_scene("SP_BPL", "team") == "sp_bpl"
    assert template_for_scene("SP_Arena", "team") == "sp_arena"
    assert template_for_scene("DP_BPL", "team") == "dp_bpl"
    assert template_for_scene("DP_Arena", "team") == "dp_arena"
    assert template_for_scene("个人赛", "knockout") == "sp_arena"
    assert template_for_scene("现场摄像", "team") == "live"
    assert template_for_scene("Live", "team") == "live"


def test_match_end_payload():
    session = MatchSession("team", _team_config())
    session.start()
    session.set_assignments(
        {"L1": {"machine": "IIDX#1", "side": "1p"}, "R1": {"machine": "IIDX#2", "side": "2p"}}
    )
    session.begin_round()
    session.on_machine_scores("IIDX#1", {"1pscore": "2000"})
    session.on_machine_scores("IIDX#2", {"2pscore": "1000"})
    session.confirm({"L1": 2000, "R1": 1000})
    session.advance()
    payload = match_end_payload(session)
    assert payload["cmd"] == "match_end"
    assert payload["data"]["rounds"][0]["winner"] == "left"


def test_overlay_push_failure_returns_false():
    pusher = OverlayPusher(uri="ws://127.0.0.1:1", timeout=0.5)
    assert pusher.push({"cmd": "round_start"}) is False


def test_overlay_hue_color_conversion():
    assert hue_for_color("#ff0000") == 0.0
    assert hue_for_color("#ffff00") == 60.0
    assert hue_for_color("#00ff00") == 120.0
    assert hue_for_color("#0000ff") == 240.0
    assert hue_for_color("#888888") == 0.0


def test_knockout_overlay_hues_follow_machine_colors():
    cfg = KnockoutConfig.model_validate(
        {"groups": {group: [f"{group}{i}" for i in range(1, 5)] for group in "ABCD"}}
    )
    session = MatchSession("knockout", cfg)
    session.start()
    payload = round_start_payload(session, "sp_arena")
    assert payload["data"]["hues"] == {
        "machine_1": 0.0,
        "machine_2": 60.0,
        "machine_3": 120.0,
        "machine_4": 240.0,
    }

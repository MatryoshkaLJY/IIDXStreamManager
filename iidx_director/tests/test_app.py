import json
from types import SimpleNamespace

import pytest

from src.app import _default_scene, create_app
from src.config.models import KnockoutConfig, TeamMatchConfig
from src.match.session import MatchSession
from src.push.scoreboard import PushError
from src.state import RuntimeState

TEAM_CONFIG = {
    "stageName": "S",
    "matchNumber": 1,
    "leftTeam": {"name": "L", "players": ["L1", "L2"]},
    "rightTeam": {"name": "R", "players": ["R1", "R2"]},
    "rounds": [
        {"type": "1v1", "theme": "T1", "leftPlayers": ["L1"], "rightPlayers": ["R1"], "points": 1},
        {"type": "1v1", "theme": "T2", "leftPlayers": ["L2"], "rightPlayers": ["R2"], "points": 2},
    ],
}


class FakeScoreboardPusher:
    def __init__(self):
        self.pushed = []
        self.fail_next = False

    def push(self, board, payload):
        if self.fail_next:
            self.fail_next = False
            raise PushError("模拟推送失败")
        self.pushed.append((board, payload))

    def push_all(self, items):
        for item in items:
            self.push(item["board"], item["payload"])


class FakeOverlayPusher:
    def __init__(self):
        self.pushed = []

    def push(self, payload):
        self.pushed.append(payload)
        return True


class FakeOBS:
    connected = True

    def switch_scene(self, name):
        pass

    def apply_match_visibility(self, scene, play_type, assignments, team_by_player):
        pass


@pytest.fixture
def env(tmp_path):
    app, socketio = create_app(config_dir=tmp_path)
    app.config["TESTING"] = True
    ctx = app.config["CONTEXT"]
    ctx.scoreboard = FakeScoreboardPusher()
    ctx.overlay = FakeOverlayPusher()
    ctx.obs = FakeOBS()
    client = app.test_client()
    return app, client, ctx


def _post(client, url, body=None):
    resp = client.post(url, json=body or {})
    assert resp.status_code == 200
    return resp.get_json()


def _upload_team_config(client):
    resp = _post(client, "/api/config/upload", {"kind": "team", "content": json.dumps(TEAM_CONFIG)})
    assert resp["success"]


def _start_team_match(client, ctx):
    _upload_team_config(client)
    resp = _post(client, "/api/mode", {"mode": "team"})
    assert resp["success"]
    resp = _post(client, "/api/match/start")
    assert resp["success"], resp
    return ctx.session


def _feed_scores(ctx, machine_ex):
    for machine, sides in machine_ex.items():
        scores = {f"{side}score": str(ex) for side, ex in sides.items()}
        ctx.session.on_machine_scores(machine, scores)


def _confirm_pending(client, ctx):
    pending = ctx.scenes.pending
    assert pending is not None
    response = _post(client, "/api/scene/pending/confirm", {"id": pending.id})
    assert response["success"], response
    return response


def test_default_scene_uses_schedule_play_type_and_round_type():
    ctx = SimpleNamespace(state=RuntimeState())
    config = TeamMatchConfig.model_validate({
        "playType": "DP",
        "leftTeam": {"name": "L", "players": ["L1", "L2"]},
        "rightTeam": {"name": "R", "players": ["R1", "R2"]},
        "rounds": [
            {"type": "1v1", "leftPlayers": ["L1"], "rightPlayers": ["R1"]},
            {"type": "2v2", "leftPlayers": ["L1", "L2"], "rightPlayers": ["R1", "R2"]},
        ],
    })
    session = MatchSession("team", config)
    session.start()
    assert _default_scene(ctx, session) == "DP_BPL"
    session.round_index = 1
    assert _default_scene(ctx, session) == "DP_Arena"

    knockout = MatchSession("knockout", KnockoutConfig.model_validate({
        "playType": "DP",
        "groups": {g: [f"{g}{i}" for i in range(1, 5)] for g in "ABCD"},
    }))
    knockout.start()
    assert _default_scene(ctx, knockout) == "DP_Arena"


# ---- 页面与基础 API ----

def test_pages_render(env):
    _, client, _ = env
    for path in ("/", "/prep", "/review"):
        assert client.get(path).status_code == 200


def test_mode_validation(env):
    _, client, _ = env
    assert _post(client, "/api/mode", {"mode": "team"})["success"]
    assert not _post(client, "/api/mode", {"mode": "weird"})["success"]


def test_config_upload_and_view(env):
    _, client, _ = env
    _upload_team_config(client)
    resp = client.get("/api/config/current/team").get_json()
    assert resp["success"] and resp["config"]["leftTeam"]["name"] == "L"
    bad = _post(client, "/api/config/upload", {"kind": "team", "content": "{bad json"})
    assert not bad["success"]


def test_match_start_with_invalid_config(env, tmp_path):
    _, client, _ = env
    (tmp_path / "team_match.json").write_text("{broken", encoding="utf-8")
    resp = _post(client, "/api/match/start")
    assert not resp["success"] and "JSON" in resp["error"]


def test_templates_auto_generated(env, tmp_path):
    # create_app 时应自动生成配置模板
    assert (tmp_path / "team_match.json").exists()
    assert (tmp_path / "knockout.json").exists()


# ---- 完整流程 ----

def test_team_match_full_api_flow(env):
    _, client, ctx = env
    session = _start_team_match(client, ctx)
    # init 已推送到 BPL
    assert ctx.scoreboard.pushed[0][0] == "bpl"
    assert ctx.scoreboard.pushed[0][1]["cmd"] == "init"

    # 第 1 回合
    resp = _post(client, "/api/round/assign", {
        "assignments": {
            "L1": {"machine": "IIDX#1", "side": "1p"},
            "R1": {"machine": "IIDX#1", "side": "2p"},
        }
    })
    assert resp["success"]
    resp = _post(client, "/api/round/begin", {"scene": "SP团队赛"})
    assert resp["success"]
    confirm = _confirm_pending(client, ctx)
    assert confirm["warnings"] == []
    # overlay round_start 已推送
    assert ctx.overlay.pushed[-1]["cmd"] == "round_start"
    assert ctx.overlay.pushed[-1]["data"]["template"] == "sp_bpl"

    _feed_scores(ctx, {"IIDX#1": {"1p": 2000, "2p": 1500}})
    assert session.phase.value == "REVIEW"

    resp = _post(client, "/api/round/confirm", {"scores": {"L1": 2000, "R1": 1500}})
    assert resp["success"]
    _confirm_pending(client, ctx)
    board, payload = ctx.scoreboard.pushed[-1]
    assert payload == {"cmd": "score", "data": {"round": 1, "leftScore": 1, "rightScore": 0}}
    assert ctx.overlay.pushed[-1]["cmd"] == "round_result"

    resp = _post(client, "/api/round/advance")
    assert resp["success"] and not resp["match_end"]

    # 第 2 回合 → 比赛结束
    _post(client, "/api/round/assign", {
        "assignments": {
            "L2": {"machine": "IIDX#2", "side": "1p"},
            "R2": {"machine": "IIDX#2", "side": "2p"},
        }
    })
    _post(client, "/api/round/begin", {})
    _confirm_pending(client, ctx)
    _feed_scores(ctx, {"IIDX#2": {"1p": 1000, "2p": 3000}})
    resp = _post(client, "/api/round/confirm", {"scores": {"L2": 1000, "R2": 3000}})
    assert resp["success"]
    _confirm_pending(client, ctx)
    assert ctx.scoreboard.pushed[-1][1]["data"] == {"round": 2, "leftScore": 0, "rightScore": 2}
    resp = _post(client, "/api/round/advance")
    assert resp["match_end"]


def test_confirm_push_failure_and_repush(env):
    _, client, ctx = env
    _start_team_match(client, ctx)
    _post(client, "/api/round/assign", {
        "assignments": {
            "L1": {"machine": "IIDX#1", "side": "1p"},
            "R1": {"machine": "IIDX#1", "side": "2p"},
        }
    })
    _post(client, "/api/round/begin", {})
    _confirm_pending(client, ctx)
    _feed_scores(ctx, {"IIDX#1": {"1p": 2000, "2p": 1500}})
    ctx.scoreboard.fail_next = True
    resp = _post(client, "/api/round/confirm", {"scores": {"L1": 2000, "R1": 1500}})
    assert resp["success"]
    pending = ctx.scenes.pending
    assert pending is not None
    resp = _post(client, "/api/scene/pending/confirm", {"id": pending.id})
    assert not resp["success"] and resp["pending"]
    resp = _post(client, "/api/round/repush")
    assert resp["success"]
    _confirm_pending(client, ctx)
    assert ctx.scoreboard.pushed[-1][1]["cmd"] == "score"


def test_confirm_edited_scores(env):
    _, client, ctx = env
    _start_team_match(client, ctx)
    _post(client, "/api/round/assign", {
        "assignments": {
            "L1": {"machine": "IIDX#1", "side": "1p"},
            "R1": {"machine": "IIDX#1", "side": "2p"},
        }
    })
    _post(client, "/api/round/begin", {})
    _confirm_pending(client, ctx)
    _feed_scores(ctx, {"IIDX#1": {"1p": 2000, "2p": 1500}})
    resp = _post(client, "/api/round/confirm", {"scores": {"L1": 100, "R1": 9000}})
    assert resp["success"]
    _confirm_pending(client, ctx)
    assert ctx.scoreboard.pushed[-1][1]["data"] == {"round": 1, "leftScore": 0, "rightScore": 1}


def test_abort(env):
    _, client, ctx = env
    _start_team_match(client, ctx)
    resp = _post(client, "/api/match/abort")
    assert resp["success"]
    assert ctx.session is None
    resp = _post(client, "/api/match/abort")
    assert not resp["success"]


def test_force_review_manual_entry(env):
    _, client, ctx = env
    _start_team_match(client, ctx)
    _post(client, "/api/round/assign", {
        "assignments": {
            "L1": {"machine": "IIDX#1", "side": "1p"},
            "R1": {"machine": "IIDX#1", "side": "2p"},
        }
    })
    _post(client, "/api/round/begin", {})
    _confirm_pending(client, ctx)
    # 抓分不可用，手动录入
    resp = _post(client, "/api/round/force_review", {"scores": {"L1": 2100, "R1": 1500}})
    assert resp["success"]
    assert ctx.session.phase.value == "REVIEW"
    assert ctx.session.last_result["winner"] == "left"
    resp = _post(client, "/api/round/confirm", {"scores": {"L1": 2100, "R1": 1500}})
    assert resp["success"]
    _confirm_pending(client, ctx)
    assert ctx.scoreboard.pushed[-1][1]["data"] == {"round": 1, "leftScore": 1, "rightScore": 0}


def test_test_mode_injects_machine_scores_and_blank_screenshot(env, tmp_path):
    _, client, ctx = env
    ctx.screenshots.root = tmp_path / "screenshots"
    _upload_team_config(client)
    assert _post(client, "/api/mode", {"mode": "team"})["success"]
    assert _post(client, "/api/test-mode", {"enabled": True})["success"]
    assert _post(client, "/api/match/start")["success"]
    _post(client, "/api/round/assign", {
        "assignments": {
            "L1": {"machine": "IIDX#1", "side": "1p"},
            "R1": {"machine": "IIDX#1", "side": "2p"},
        }
    })
    _post(client, "/api/round/begin", {})
    _confirm_pending(client, ctx)

    response = _post(client, "/api/test/scores", {
        "machine_id": "IIDX#1",
        "scores": {"1p": 2100, "2p": 1500},
    })
    assert response["success"] and response["phase"] == "REVIEW"
    snap = client.get("/api/state").get_json()
    image = client.get(snap["screenshots"]["IIDX#1"])
    assert image.status_code == 200 and image.content_type == "image/png"
    assert image.data

    assert _post(client, "/api/match/abort")["success"]
    assert _post(client, "/api/test-mode", {"enabled": False})["success"]


def test_assign_without_match(env):
    _, client, _ = env
    resp = _post(client, "/api/round/assign", {"assignments": {}})
    assert not resp["success"]

import json

from src.app import create_app


TEAM_CONFIG = {
    "stageName": "S",
    "matchNumber": 1,
    "leftTeam": {"name": "L", "players": ["L1"]},
    "rightTeam": {"name": "R", "players": ["R1"]},
    "rounds": [
        {"type": "1v1", "theme": "T1", "leftPlayers": ["L1"], "rightPlayers": ["R1"], "points": 1},
    ],
}


class Scoreboard:
    def __init__(self, events=None):
        self.events = events if events is not None else []
        self.pushed = []

    def push(self, board, payload):
        self.pushed.append((board, payload))

    def push_all(self, items):
        self.events.append("push")
        self.pushed.extend((item["board"], item["payload"]) for item in items)


class Overlay:
    def push(self, payload):
        return True


class OBS:
    connected = True

    def __init__(self, events):
        self.events = events

    def switch_scene(self, scene):
        self.events.append(("switch", scene))


class VisibilityOBS(OBS):
    def __init__(self, events, fail=False):
        super().__init__(events)
        self.fail = fail

    def apply_match_visibility(self, scene, play_type, assignments, team_by_player):
        self.events.append(("visibility", scene, play_type, assignments, team_by_player))
        if self.fail:
            raise RuntimeError("模拟可见性失败")


def _post(client, path, payload=None):
    response = client.post(path, json=payload or {})
    assert response.status_code == 200
    return response.get_json()


def _confirm_pending(client, ctx):
    pending = ctx.scenes.pending
    assert pending is not None
    response = _post(client, "/api/scene/pending/confirm", {"id": pending.id})
    assert response["success"], response
    return response


def _capture_scores(ctx):
    ctx.session.on_machine_scores("IIDX#1", {"1pscore": "2000", "2pscore": "1500"})


def _setup(tmp_path, scene_events=None):
    app, _ = create_app(config_dir=tmp_path / "config")
    app.config["TESTING"] = True
    client = app.test_client()
    ctx = app.config["CONTEXT"]
    ctx.screenshots.root = tmp_path / "screenshots"
    if scene_events is not None:
        ctx.obs = OBS(scene_events)
    ctx.scoreboard = Scoreboard()
    ctx.overlay = Overlay()
    assert _post(client, "/api/config/upload", {"kind": "team", "content": json.dumps(TEAM_CONFIG)})["success"]
    assert _post(client, "/api/mode", {"mode": "team"})["success"]
    assert _post(client, "/api/match/start")["success"]
    assert _post(client, "/api/round/assign", {
        "assignments": {
            "L1": {"machine": "IIDX#1", "side": "1p"},
            "R1": {"machine": "IIDX#1", "side": "2p"},
        },
    })["success"]
    assert _post(client, "/api/round/begin", {"scene": "SP团队赛"})["success"]
    ctx.session.on_machine_scores("IIDX#1", {"1pscore": "2000", "2pscore": "1500"})
    return client, ctx


def test_begin_does_not_switch_scene(tmp_path):
    events = []
    _client, _ctx = _setup(tmp_path, events)
    assert events == []


def test_confirm_switches_waits_then_pushes(tmp_path):
    client, ctx = _setup(tmp_path)
    events = []
    ctx.obs = OBS(events)
    ctx.scoreboard = Scoreboard(events)
    ctx.sleep = lambda seconds: events.append(("sleep", seconds))
    _confirm_pending(client, ctx)
    events.clear()
    _capture_scores(ctx)

    response = _post(client, "/api/round/confirm", {"scores": {"L1": 2000, "R1": 1500}})

    assert response["success"]
    _confirm_pending(client, ctx)
    assert events == [("switch", ctx.state.scenes["scoreboard"]), ("sleep", 5.0), "push"]


def test_advance_does_not_switch_scene(tmp_path):
    client, ctx = _setup(tmp_path)
    events = []
    ctx.obs = OBS(events)
    ctx.scoreboard = Scoreboard()
    ctx.sleep = lambda seconds: None
    _confirm_pending(client, ctx)
    events.clear()
    _capture_scores(ctx)
    assert _post(client, "/api/round/confirm", {"scores": {"L1": 2000, "R1": 1500}})["success"]
    _confirm_pending(client, ctx)
    events.clear()

    response = _post(client, "/api/round/advance")

    assert response["match_end"]
    assert events == []


def test_scene_switch_api_and_screenshot_url(tmp_path):
    client, ctx = _setup(tmp_path)
    events = []
    ctx.obs = OBS(events)
    _post(client, "/api/scene/pending/cancel", {"id": ctx.scenes.pending.id})
    ctx.screenshots.save("round-1", "IIDX#1", b"png-data")

    response = _post(client, "/api/obs/switch", {"scene": "scoreboard"})
    assert response["success"]
    _confirm_pending(client, ctx)
    state = client.get("/api/state").get_json()

    assert events == [("switch", ctx.state.scenes["scoreboard"])]
    assert "IIDX#1" in state["screenshots"]
    image = client.get(state["screenshots"]["IIDX#1"])
    assert image.status_code == 200
    assert image.data == b"png-data"


def test_scene_switch_uses_actual_obs_scene_name(tmp_path):
    client, ctx = _setup(tmp_path)
    events = []
    ctx.obs = OBS(events)
    _post(client, "/api/scene/pending/cancel", {"id": ctx.scenes.pending.id})

    response = _post(client, "/api/obs/switch", {"scene": "team_sp_1v1"})
    assert response["success"]
    _confirm_pending(client, ctx)

    assert response["scene"] == "SP_BPL"
    assert events == [("switch", "SP_BPL")]


def test_test_mode_keeps_obs_scene_switching(tmp_path):
    client, ctx = _setup(tmp_path)
    events = []
    ctx.obs = OBS(events)

    assert _post(client, "/api/match/abort")["success"]
    assert _post(client, "/api/test-mode", {"enabled": True})["success"]
    response = _post(client, "/api/obs/switch", {"scene": "team_sp_2v2"})
    assert response["success"]
    _confirm_pending(client, ctx)

    assert response["scene"] == "SP_Arena"
    assert events == [("switch", "SP_Arena")]
    assert _post(client, "/api/test-mode", {"enabled": False})["success"]


def test_round_begin_confirm_applies_match_visibility(tmp_path):
    events = []
    client, ctx = _setup(tmp_path)
    ctx.obs = VisibilityOBS(events)

    response = _post(client, "/api/scene/pending/confirm", {
        "id": ctx.scenes.pending.id,
    })

    assert response["success"]
    assert events[0] == ("switch", "SP_BPL")
    assert events[1][0:3] == ("visibility", "SP_BPL", "SP")
    assert ctx.session.phase.value == "LIVE"


def test_visibility_failure_keeps_pending_for_retry(tmp_path):
    events = []
    client, ctx = _setup(tmp_path)
    ctx.obs = VisibilityOBS(events, fail=True)

    response = _post(client, "/api/scene/pending/confirm", {
        "id": ctx.scenes.pending.id,
    })

    assert not response["success"]
    assert ctx.session.phase.value == "PREP"
    assert ctx.scenes.pending is not None
    assert ctx.scenes.pending.status == "failed"
    assert ctx.scenes.pending.failed_stage == "action"

    ctx.obs = VisibilityOBS(events)
    retry = _post(client, "/api/scene/pending/confirm", {
        "id": ctx.scenes.pending.id,
    })
    assert retry["success"]
    assert ctx.session.phase.value == "LIVE"

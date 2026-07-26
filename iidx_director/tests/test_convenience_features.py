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


def _post(client, path, payload=None):
    response = client.post(path, json=payload or {})
    assert response.status_code == 200
    return response.get_json()


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

    response = _post(client, "/api/round/confirm", {"scores": {"L1": 2000, "R1": 1500}})

    assert response["success"]
    assert events == [("switch", ctx.state.scenes["scoreboard"]), ("sleep", 5.0), "push"]


def test_advance_does_not_switch_scene(tmp_path):
    client, ctx = _setup(tmp_path)
    events = []
    ctx.obs = OBS(events)
    ctx.scoreboard = Scoreboard()
    ctx.sleep = lambda seconds: None
    assert _post(client, "/api/round/confirm", {"scores": {"L1": 2000, "R1": 1500}})["success"]
    events.clear()

    response = _post(client, "/api/round/advance")

    assert response["match_end"]
    assert events == []


def test_scene_switch_api_and_screenshot_url(tmp_path):
    client, ctx = _setup(tmp_path)
    events = []
    ctx.obs = OBS(events)
    ctx.screenshots.save("round-1", "IIDX#1", b"png-data")

    response = _post(client, "/api/obs/switch", {"scene": "scoreboard"})
    state = client.get("/api/state").get_json()

    assert response["success"]
    assert events == [("switch", ctx.state.scenes["scoreboard"])]
    assert "IIDX#1" in state["screenshots"]
    image = client.get(state["screenshots"]["IIDX#1"])
    assert image.status_code == 200
    assert image.data == b"png-data"


def test_scene_switch_uses_actual_obs_scene_name(tmp_path):
    client, ctx = _setup(tmp_path)
    events = []
    ctx.obs = OBS(events)

    response = _post(client, "/api/obs/switch", {"scene": "team_sp_1v1"})

    assert response["success"]
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
    assert response["scene"] == "SP_Arena"
    assert events == [("switch", "SP_Arena")]
    assert _post(client, "/api/test-mode", {"enabled": False})["success"]

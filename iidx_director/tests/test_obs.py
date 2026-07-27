import time
from unittest import mock

import pytest
from PIL import Image

from src.obs import monitor as monitor_module
from src.obs.client import OBSClient
from src.obs.monitor import CabinetMonitor


# ---- OBSClient ----

def _make_client():
    with mock.patch("src.obs.client.obsws_python.ReqClient") as req:
        client = OBSClient(password="secret")
        client.connect()
    return client, req


def test_client_connect_verifies_version():
    client, req = _make_client()
    req.return_value.get_version.assert_called_once()
    assert client.connected


def test_client_get_scenes():
    client, req = _make_client()
    req.return_value.send.return_value = {"scenes": [{"sceneName": "现场摄像"}, {"sceneName": "SP团队赛"}]}
    assert client.get_scenes() == ["现场摄像", "SP团队赛"]
    req.return_value.send.assert_called_with("GetSceneList", raw=True)


def test_client_switch_scene():
    client, req = _make_client()
    client.switch_scene("SP团队赛")
    req.return_value.set_current_program_scene.assert_called_with("SP团队赛")


def test_client_require_connection():
    with pytest.raises(RuntimeError, match="未连接"):
        OBSClient().switch_scene("x")


def test_client_applies_sp_arena_visibility():
    client, req = _make_client()

    def send(request, data=None, raw=False):
        if request == "GetSceneItemList":
            groups = [
                f"SP_C{machine}_{side}"
                for machine in range(1, 5)
                for side in ("1P", "2P")
            ] + [
                f"SP_MIDUI_{side}" for side in ("1P", "2P")
            ] + [
                f"SP_{side}_{suffix}"
                for side in ("1P", "2P")
                for suffix in ("SongName", "BPM")
            ]
            return {"sceneItems": [
                {"sourceName": name, "sceneItemId": index}
                for index, name in enumerate(groups, start=1)
            ]}
        if request == "GetGroupSceneItemList":
            return {
                "sceneItems": [
                    {"sourceName": f"IIDX#{i}", "sceneItemId": i} for i in range(1, 5)
                ]
            }
        return {}

    req.return_value.send.side_effect = send
    client.apply_match_visibility(
        "SP_Arena", "SP", {"p": {"machine": "IIDX#2", "side": "1p"}}
    )

    enabled = [
        call.args[1]
        for call in req.return_value.send.call_args_list
        if call.args[0] == "SetSceneItemEnabled" and call.args[1]["sceneItemEnabled"]
    ]
    assert any(item["sceneName"] == "SP_Arena" for item in enabled)
    assert any(item["sceneName"] == "SP_MIDUI_1P" and item["sceneItemId"] == 1 for item in enabled)
    assert not any(item["sceneName"] == "SP_MIDUI_2P" and item["sceneItemEnabled"] for item in enabled)


def test_client_dp_bpl_public_groups_show_both_machines():
    client, req = _make_client()

    def send(request, data=None, raw=False):
        if request == "GetSceneItemList":
            groups = ["DP_LJUDGE", "DP_LUI", "DP_RJUDGE", "DP_RUI", "DP_LCAM", "DP_RCAM"]
            groups += ["Gauges", "DP_SongName", "DP_BPM"]
            return {"sceneItems": [
                {"sourceName": name, "sceneItemId": index}
                for index, name in enumerate(groups, start=1)
            ]}
        if request == "GetGroupSceneItemList":
            return {
                "sceneItems": [
                    {"sourceName": f"IIDX#{i}", "sceneItemId": i} for i in range(1, 5)
                ] + [{"sourceName": f"CAM#{i}", "sceneItemId": i + 10} for i in range(1, 5)]
            }
        return {}

    req.return_value.send.side_effect = send
    client.apply_match_visibility(
        "DP_BPL", "DP",
        {
            "left": {"machine": "IIDX#1", "side": "1p"},
            "right": {"machine": "IIDX#3", "side": "2p"},
        },
        {"left": "L", "right": "R"},
    )

    public_enabled = []
    for call in req.return_value.send.call_args_list:
        if call.args[0] == "SetSceneItemEnabled":
            data = call.args[1]
            if data["sceneName"] == "Gauges" and data["sceneItemEnabled"]:
                public_enabled.append(data["sceneItemId"])
    assert sorted(public_enabled) == [1, 3]


def test_client_visibility_requires_target_element():
    client, req = _make_client()

    def send(request, data=None, raw=False):
        if request == "GetSceneItemList":
            return {"sceneItems": [
                {"sourceName": name, "sceneItemId": index}
                for index, name in enumerate(("Gauges", "DP_SongName", "DP_BPM"), start=1)
            ]}
        if request == "GetGroupSceneItemList":
            return {"sceneItems": []}
        return {}

    req.return_value.send.side_effect = send
    with pytest.raises(RuntimeError, match="缺少元素"):
        client.apply_match_visibility(
            "DP_Arena", "DP", {"p": {"machine": "IIDX#1", "side": "1p"}}
        )


# ---- CabinetMonitor ----

class FakeOBSManager:
    instances = []

    def __init__(self, host, port, password):
        self.results = {}
        self.last_score_frame = None
        self.capture_calls = 0
        self.registered = []
        FakeOBSManager.instances.append(self)

    def connect(self):
        pass

    def init_state_machine(self, config_path, simple_mode):
        self.state_machine_config = config_path
        self.simple_mode = simple_mode

    def register_machine(self, machine_id, source_name):
        self.registered.append((machine_id, source_name))

    def capture_source(self, source_name, target_size=None, image_format="png"):
        self.capture_calls += 1
        return Image.new("RGB", target_size or (10, 10), "red")

    def process_frame(self, machine_id):
        result = self.results.get(machine_id, {"machine_id": machine_id, "scores": None})
        self.last_score_frame = Image.new("RGB", (10, 10), "red") if result.get("scores") else None
        return result


def test_monitor_dispatches_scores_and_updates(monkeypatch):
    monkeypatch.setattr(monitor_module, "OBSManager", FakeOBSManager)
    updates, scores = [], []
    mon = CabinetMonitor(
        machines={"IIDX#1": "SRC1"}, interval=0.05,
        on_scores=lambda m, s: scores.append((m, s)),
        on_update=lambda r: updates.append(r),
    )
    FakeOBSManager.instances.clear()
    mon.start()
    try:
        mgr = FakeOBSManager.instances[0]
        assert mgr.registered == [("IIDX#1", "SRC1")]
        assert mgr.simple_mode is True
        mgr.results["IIDX#1"] = {
            "machine_id": "IIDX#1",
            "scores": {"1pscore": "12345", "1p_valid": True},
        }
        deadline = time.time() + 3
        while not scores and time.time() < deadline:
            time.sleep(0.02)
        assert scores == [("IIDX#1", {"1pscore": "12345", "1p_valid": True})]
        assert updates  # 每帧都有 on_update
    finally:
        mon.stop()
    assert not mon.running


def test_monitor_dispatches_score_frame(monkeypatch):
    monkeypatch.setattr(monitor_module, "OBSManager", FakeOBSManager)
    frames = []
    mon = CabinetMonitor(
        machines={"IIDX#1": "SRC1"}, interval=0.05,
        on_scores=lambda m, s: None,
        on_score_frame=lambda m, png: frames.append((m, png)),
    )
    FakeOBSManager.instances.clear()
    mon.start()
    try:
        mgr = FakeOBSManager.instances[0]
        mgr.results["IIDX#1"] = {
            "machine_id": "IIDX#1",
            "scores": {"1pscore": "12345", "1p_valid": True},
        }
        deadline = time.time() + 3
        while not frames and time.time() < deadline:
            time.sleep(0.02)
        assert frames and frames[0][0] == "IIDX#1"
        assert frames[0][1].startswith(b"\x89PNG")
        assert not getattr(mgr, "capture_calls", 0)
    finally:
        mon.stop()


def test_monitor_survives_frame_errors(monkeypatch):
    class BrokenManager(FakeOBSManager):
        def process_frame(self, machine_id):
            raise RuntimeError("obs 断了")

    monkeypatch.setattr(monitor_module, "OBSManager", BrokenManager)
    mon = CabinetMonitor(machines={"IIDX#1": "SRC1"}, interval=0.05)
    mon.start()
    time.sleep(0.2)
    assert mon.running  # 异常不杀线程
    mon.stop()
    assert not mon.running


def test_monitor_requires_obs_manager(monkeypatch):
    monkeypatch.setattr(monitor_module, "OBSManager", None)
    with pytest.raises(RuntimeError, match="obs_manager 不可用"):
        CabinetMonitor().start()

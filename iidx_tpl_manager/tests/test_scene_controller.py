from unittest.mock import MagicMock

import pytest

from obsws_python.error import OBSSDKRequestError

from src.obs.client import OBSClient
from src.obs.scene_controller import REQUIRED_SCENES, SceneController


class TestSceneController:
    def test_validate_scenes_returns_false_when_not_connected(self):
        obs = MagicMock(spec=OBSClient)
        obs.connected = False
        ctrl = SceneController(obs)
        ok, missing = ctrl.validate_scenes()
        assert ok is False
        assert missing == []
        assert ctrl.scenes_valid is False

    def test_validate_scenes_returns_true_when_all_scenes_present(self):
        obs = MagicMock(spec=OBSClient)
        obs.connected = True
        obs.get_scene_list.return_value = {
            "scenes": [
                {"sceneName": "现场摄像"},
                {"sceneName": "SP团队赛"},
                {"sceneName": "DP团队赛"},
                {"sceneName": "个人赛"},
            ]
        }
        ctrl = SceneController(obs)
        ok, missing = ctrl.validate_scenes()
        assert ok is True
        assert missing == []
        assert ctrl.scenes_valid is True

    def test_validate_scenes_returns_missing_scenes(self):
        obs = MagicMock(spec=OBSClient)
        obs.connected = True
        obs.get_scene_list.return_value = {
            "scenes": [
                {"sceneName": "现场摄像"},
                {"sceneName": "SP团队赛"},
            ]
        }
        ctrl = SceneController(obs)
        ok, missing = ctrl.validate_scenes()
        assert ok is False
        assert "DP团队赛" in missing
        assert "个人赛" in missing
        assert ctrl.scenes_valid is False

    def test_switch_to_returns_not_ready_when_disconnected(self):
        obs = MagicMock(spec=OBSClient)
        obs.connected = False
        ctrl = SceneController(obs)
        ok, msg = ctrl.switch_to("现场摄像")
        assert ok is False
        assert msg == "OBS not ready"

    def test_switch_to_returns_not_ready_when_scenes_invalid(self):
        obs = MagicMock(spec=OBSClient)
        obs.connected = True
        ctrl = SceneController(obs)
        ctrl.scenes_valid = False
        ok, msg = ctrl.switch_to("现场摄像")
        assert ok is False
        assert msg == "OBS not ready"

    def test_switch_to_calls_set_current_program_scene_for_valid_scene(self):
        obs = MagicMock(spec=OBSClient)
        obs.connected = True
        obs.get_scene_list.return_value = {
            "scenes": [
                {"sceneName": "现场摄像"},
                {"sceneName": "SP团队赛"},
                {"sceneName": "DP团队赛"},
                {"sceneName": "个人赛"},
            ]
        }
        ctrl = SceneController(obs)
        ctrl.validate_scenes()
        ok, msg = ctrl.switch_to("SP团队赛")
        assert ok is True
        assert msg == ""
        obs.set_current_program_scene.assert_called_once_with("SP团队赛")

    def test_switch_to_catches_obs_sdk_request_error(self):
        obs = MagicMock(spec=OBSClient)
        obs.connected = True
        obs.get_scene_list.return_value = {
            "scenes": [
                {"sceneName": "现场摄像"},
                {"sceneName": "SP团队赛"},
                {"sceneName": "DP团队赛"},
                {"sceneName": "个人赛"},
            ]
        }
        obs.set_current_program_scene.side_effect = OBSSDKRequestError("missing scene", 100, "scene not found")
        ctrl = SceneController(obs)
        ctrl.validate_scenes()
        ok, msg = ctrl.switch_to("现场摄像")
        assert ok is False
        assert "missing scene" in msg

    def test_switch_to_rejects_unknown_scene_name(self):
        obs = MagicMock(spec=OBSClient)
        obs.connected = True
        obs.get_scene_list.return_value = {
            "scenes": [
                {"sceneName": "现场摄像"},
                {"sceneName": "SP团队赛"},
                {"sceneName": "DP团队赛"},
                {"sceneName": "个人赛"},
            ]
        }
        ctrl = SceneController(obs)
        ctrl.validate_scenes()
        ok, msg = ctrl.switch_to("UnknownScene")
        assert ok is False
        assert msg == "Unknown scene"

    def test_validate_scenes_catches_exception(self):
        obs = MagicMock(spec=OBSClient)
        obs.connected = True
        obs.get_scene_list.side_effect = RuntimeError("boom")
        ctrl = SceneController(obs)
        ok, missing = ctrl.validate_scenes()
        assert ok is False
        assert missing == []

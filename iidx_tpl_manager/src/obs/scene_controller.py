from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from obsws_python.error import OBSSDKRequestError

if TYPE_CHECKING:
    from src.obs.client import OBSClient

REQUIRED_SCENES = {
    "live": "现场摄像",
    "sp_team": "SP团队赛",
    "dp_team": "DP团队赛",
    "individual": "个人赛",
}


class SceneController:
    """Validates and switches between required OBS scenes."""

    def __init__(self, obs_client: "OBSClient") -> None:
        self.obs = obs_client
        self.scenes_valid = False
        self.missing_scenes: List[str] = []

    def validate_scenes(self) -> Tuple[bool, List[str]]:
        if not self.obs.connected:
            self.scenes_valid = False
            self.missing_scenes = []
            return False, []

        try:
            response: Dict[str, Any] = self.obs.get_scene_list(raw=True)
            scenes = response.get("scenes", [])
            available = {s.get("sceneName") for s in scenes if isinstance(s, dict)}
            missing = [s for s in REQUIRED_SCENES.values() if s not in available]
            self.scenes_valid = len(missing) == 0
            self.missing_scenes = missing
            return self.scenes_valid, self.missing_scenes
        except Exception:
            self.scenes_valid = False
            self.missing_scenes = []
            return False, []

    def switch_to(self, scene_name: str) -> Tuple[bool, str]:
        if not self.obs.connected or not self.scenes_valid:
            return False, "OBS not ready"

        if scene_name not in REQUIRED_SCENES.values():
            return False, "Unknown scene"

        try:
            self.obs.set_current_program_scene(scene_name)
            return True, ""
        except OBSSDKRequestError as e:
            return False, str(e)

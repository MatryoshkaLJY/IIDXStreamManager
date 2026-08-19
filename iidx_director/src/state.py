"""运行时状态：非敏感配置持久化到 runtime/state.json（锚定模块目录）。

OBS 密码不入盘：由环境变量 IIDX_OBS_PASSWORD 或连接时表单提供，仅存内存。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

MODULE_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = MODULE_ROOT / "runtime"
STATE_FILE = RUNTIME_DIR / "state.json"

DEFAULT_SCENES = {
    "live": "Live",
    "team_sp_1v1": "SP_BPL",
    "team_sp_2v2": "SP_Arena",
    "team_dp_1v1": "DP_BPL",
    "team_dp_2v2": "DP_Arena",
    "individual_sp": "SP_Arena",
    "individual_dp": "DP_Arena",
    "grid": "Grid",
    "scoreboard": "Scoreboard_web",
}

DEFAULT_MACHINES = {f"IIDX#{i}": f"IIDX#{i}" for i in range(1, 5)}


@dataclass
class RuntimeState:
    obs_host: str = "localhost"
    obs_port: int = 4455
    mode: str = "team"  # team | knockout | knockout_ef | knockout_final
    test_mode: bool = False
    scenes: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_SCENES))
    machines: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_MACHINES))
    monitor_interval: float = 1.0
    serial_audio: dict[str, Any] = field(
        default_factory=lambda: {
            "enabled": False,
            "port": None,
            "baudrate": 9600,
            "timeout": 1.0,
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_runtime_state(path: Path = STATE_FILE) -> RuntimeState:
    if not path.exists():
        return RuntimeState()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        state = RuntimeState()
        for key, value in raw.items():
            if key == "scenes" and isinstance(value, dict):
                scenes = dict(DEFAULT_SCENES)
                scenes.update(value)
                # Migrate only the shipped legacy defaults; custom operator
                # scene names remain untouched.
                if value.get("live") == "现场摄像":
                    scenes["live"] = DEFAULT_SCENES["live"]
                if value.get("team_sp") == "SP团队赛":
                    scenes["team_sp_1v1"] = DEFAULT_SCENES["team_sp_1v1"]
                if value.get("team_dp") == "DP团队赛":
                    scenes["team_dp_1v1"] = DEFAULT_SCENES["team_dp_1v1"]
                if value.get("individual") == "个人赛":
                    scenes["individual_sp"] = DEFAULT_SCENES["individual_sp"]
                # The previous scene update stored logical labels as if they
                # were OBS scene names. Replace those shipped values with the
                # actual OBS scenes while preserving custom operator names.
                scene_name_migrations = {
                    "SP团队赛1V1": "SP_BPL",
                    "SP团队赛2V2": "SP_Arena",
                    "DP团队赛1V1": "DP_BPL",
                    "DP团队赛2V2": "DP_Arena",
                    "SP个人赛": "SP_Arena",
                    "DP个人赛": "DP_Arena",
                    "SP团队赛": "SP_BPL",
                    "DP团队赛": "DP_BPL",
                    "个人赛": "SP_Arena",
                    "现场摄像": "Live",
                    "计分板": "Scoreboard_web",
                }
                for scene_key, scene_value in list(scenes.items()):
                    if scene_value in scene_name_migrations:
                        scenes[scene_key] = scene_name_migrations[scene_value]
                for legacy_key, legacy_value in {
                    "live": "现场摄像",
                    "team_sp": "SP团队赛",
                    "team_dp": "DP团队赛",
                    "individual": "个人赛",
                }.items():
                    if value.get(legacy_key) == legacy_value:
                        scenes.pop(legacy_key, None)
                setattr(state, key, scenes)
                continue
            if hasattr(state, key):
                setattr(state, key, value)
        return state
    except (json.JSONDecodeError, TypeError):
        return RuntimeState()


def save_runtime_state(state: RuntimeState, path: Path = STATE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

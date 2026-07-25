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
    "live": "现场摄像",
    "team_sp": "SP团队赛",
    "team_dp": "DP团队赛",
    "individual": "个人赛",
    "scoreboard": "Scoreboard_web",
}

DEFAULT_MACHINES = {f"IIDX#{i}": f"IIDX#{i}" for i in range(1, 5)}


@dataclass
class RuntimeState:
    obs_host: str = "localhost"
    obs_port: int = 4455
    mode: str = "team"  # team | knockout
    scenes: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_SCENES))
    machines: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_MACHINES))
    monitor_interval: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_runtime_state(path: Path = STATE_FILE) -> RuntimeState:
    if not path.exists():
        return RuntimeState()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        state = RuntimeState()
        for key, value in raw.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return state
    except (json.JSONDecodeError, TypeError):
        return RuntimeState()


def save_runtime_state(state: RuntimeState, path: Path = STATE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

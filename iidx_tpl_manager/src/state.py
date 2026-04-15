import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Optional


RUNTIME_STATE_PATH = Path("runtime/state.json")


@dataclass
class RuntimeState:
    config_paths: Dict[str, str] = field(default_factory=dict)
    loaded_at: Optional[str] = None
    obs_host: str = "localhost"
    obs_port: int = 4455
    obs_password: str = ""
    obs_connected: bool = False


def save_runtime_state(state: RuntimeState, path: Path = RUNTIME_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(state), f, indent=2)


def load_runtime_state(path: Path = RUNTIME_STATE_PATH) -> RuntimeState:
    if not path.exists():
        return RuntimeState()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return RuntimeState(
        config_paths=data.get("config_paths", {}),
        loaded_at=data.get("loaded_at"),
        obs_host=data.get("obs_host", "localhost"),
        obs_port=data.get("obs_port", 4455),
        obs_password=data.get("obs_password", ""),
        obs_connected=data.get("obs_connected", False),
    )

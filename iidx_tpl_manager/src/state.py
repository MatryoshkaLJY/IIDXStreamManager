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
    mode: str = ""
    current_round: int = 1
    cabinet_assignments: Dict[str, str] = field(default_factory=lambda: {"IIDX#1": "Unassigned", "IIDX#2": "Unassigned", "IIDX#3": "Unassigned", "IIDX#4": "Unassigned"})
    monitor_interval: float = 1.0
    monitoring_active: bool = False
    source_names: Dict[str, str] = field(default_factory=lambda: {
        "IIDX#1": "IIDX#1",
        "IIDX#2": "IIDX#2",
        "IIDX#3": "IIDX#3",
        "IIDX#4": "IIDX#4",
    })
    state_machine_config: str = "iidx_state_machine/state_machine.yaml"


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
        mode=data.get("mode", ""),
        current_round=data.get("current_round", 1),
        cabinet_assignments=data.get("cabinet_assignments", {"IIDX#1": "Unassigned", "IIDX#2": "Unassigned", "IIDX#3": "Unassigned", "IIDX#4": "Unassigned"}),
        monitor_interval=data.get("monitor_interval", 1.0),
        monitoring_active=data.get("monitoring_active", False),
        source_names=data.get("source_names", {
            "IIDX#1": "IIDX#1",
            "IIDX#2": "IIDX#2",
            "IIDX#3": "IIDX#3",
            "IIDX#4": "IIDX#4",
        }),
        state_machine_config=data.get("state_machine_config", "iidx_state_machine/state_machine.yaml"),
    )

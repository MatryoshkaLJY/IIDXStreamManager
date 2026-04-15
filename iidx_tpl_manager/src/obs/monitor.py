import json
import logging
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from flask_socketio import SocketIO

try:
    from obs_manager.obs_manager import OBSManager
except ImportError:
    # obs_manager is in a sibling directory to the project root
    project_root = str(Path(__file__).resolve().parents[3])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from obs_manager.obs_manager import OBSManager

from src.state import RuntimeState, load_runtime_state

logger = logging.getLogger(__name__)

DEFAULT_STATE_MACHINE_CONFIG = "iidx_state_machine/state_machine.yaml"
DEFAULT_MACHINES = ["IIDX#1", "IIDX#2", "IIDX#3", "IIDX#4"]


class CabinetMonitor:
    """Background worker that polls cabinets via OBSManager and emits updates."""

    def __init__(
        self,
        socketio: SocketIO,
        state_machine_config: str = DEFAULT_STATE_MACHINE_CONFIG,
    ) -> None:
        self.socketio = socketio
        self.state_machine_config = state_machine_config
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._obs_manager: Optional[OBSManager] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        with self._lock:
            if self._obs_manager is not None:
                try:
                    self._obs_manager.disconnect()
                except Exception:
                    pass
                self._obs_manager = None

    def _ensure_obs_manager(self) -> Optional[OBSManager]:
        with self._lock:
            if self._obs_manager is not None and self._obs_manager.is_connected():
                return self._obs_manager

            runtime_state = load_runtime_state()
            obs = OBSManager(
                host=runtime_state.obs_host,
                port=runtime_state.obs_port,
                password=runtime_state.obs_password or None,
                timeout=5,
            )
            try:
                obs.connect()
            except Exception as exc:
                logger.warning("CabinetMonitor failed to connect to OBS: %s", exc)
                return None

            try:
                obs.init_state_machine(self.state_machine_config, log_level="INFO", simple_mode=True)
            except Exception as exc:
                logger.warning("CabinetMonitor failed to init state machine: %s", exc)
                try:
                    obs.disconnect()
                except Exception:
                    pass
                return None

            for machine_id in DEFAULT_MACHINES:
                source_name = runtime_state.source_names.get(machine_id, machine_id)
                obs.register_machine(
                    machine_id=machine_id,
                    source_name=source_name,
                    state_infer_addr=("127.0.0.1", 9876),
                    score_infer_addr=("127.0.0.1", 9877),
                )

            self._obs_manager = obs
            return obs

    def _run(self) -> None:
        while not self._stop.is_set():
            runtime_state = load_runtime_state()
            interval = float(runtime_state.monitor_interval)
            if interval < 0.1:
                interval = 0.1
            if interval > 60.0:
                interval = 60.0

            obs = self._ensure_obs_manager()
            if obs is None:
                self._stop.wait(interval)
                continue

            for machine_id in DEFAULT_MACHINES:
                if self._stop.is_set():
                    break
                try:
                    result = obs.process_frame(machine_id)
                except Exception as exc:
                    logger.warning("process_frame failed for %s: %s", machine_id, exc)
                    continue

                payload: Dict[str, Any] = {
                    "machine_id": result.get("machine_id", machine_id),
                    "label": result.get("label"),
                    "state": result.get("state"),
                    "scores": result.get("scores"),
                    "score_validation_pending": result.get("score_validation_pending", False),
                }

                # Console output: single JSON line per D-15
                print(json.dumps(payload, ensure_ascii=False, default=str))

                self.socketio.emit("cabinet_update", payload)

            self._stop.wait(interval)

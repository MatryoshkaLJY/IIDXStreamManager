import threading
from typing import Any

from flask_socketio import SocketIO


class OBSHeartbeat:
    """Background heartbeat that monitors OBS connection health.

    Emits obs_status events at a fixed interval. Does NOT auto-reconnect.
    """

    def __init__(
        self,
        obs_client: Any,
        socketio: SocketIO,
        interval: float = 3.0,
    ) -> None:
        self.obs = obs_client
        self.socketio = socketio
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval + 1)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                if self.obs.connected:
                    self.obs.get_version()
            except Exception:
                self.obs.connected = False
                try:
                    self.obs.disconnect()
                except Exception:
                    pass
            self.socketio.emit("obs_status", {"connected": self.obs.connected})
            self._stop.wait(self.interval)

from typing import Any, Dict, Optional

import obsws_python
from obsws_python.error import OBSSDKError


class OBSClient:
    """Lazy-connect OBS WebSocket v5 client wrapper."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 4455,
        password: str = "",
    ) -> None:
        self.host = host
        self.port = port
        self.password = password
        self._client: Optional[obsws_python.ReqClient] = None

    def connect(self) -> None:
        self._client = obsws_python.ReqClient(
            host=self.host,
            port=self.port,
            password=self.password,
            timeout=3,
        )

    def disconnect(self) -> None:
        if self._client is not None:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None

    @property
    def connected(self) -> bool:
        if self._client is None:
            return False
        try:
            return self._client.base_client.ws.connected
        except Exception:
            return False

    @connected.setter
    def connected(self, value: bool) -> None:
        if not value and self._client is not None:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None

    def get_version(self) -> Any:
        if self._client is None:
            raise RuntimeError("OBS client is not connected")
        return self._client.get_version()

    def get_scene_list(self, raw: bool = False) -> Any:
        if self._client is None:
            raise RuntimeError("OBS client is not connected")
        return self._client.send("GetSceneList", raw=raw)

    def set_current_program_scene(self, name: str) -> None:
        if self._client is None:
            raise RuntimeError("OBS client is not connected")
        self._client.set_current_program_scene(name)

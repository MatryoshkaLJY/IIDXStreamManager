"""OBS 场景控制连接（唯一的 obsws 控制通道，端口 4455）。

机台截图走 obs_manager.OBSManager 的独立连接（见 monitor.py），
本类只负责场景列表与切换。
"""

from __future__ import annotations

import obsws_python


class OBSClient:
    def __init__(self, host: str = "localhost", port: int = 4455, password: str | None = None,
                 timeout: int = 3) -> None:
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._client: obsws_python.ReqClient | None = None

    @property
    def connected(self) -> bool:
        return self._client is not None

    def connect(self) -> None:
        self.disconnect()
        self._client = obsws_python.ReqClient(
            host=self.host, port=self.port, password=self.password or "", timeout=self.timeout
        )
        self._client.get_version()  # 验证连接

    def disconnect(self) -> None:
        if self._client is not None:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None

    def get_scenes(self) -> list[str]:
        self._require()
        resp = self._client.send("GetSceneList", raw=True)  # type: ignore[union-attr]
        return [s["sceneName"] for s in resp.get("scenes", [])]

    def switch_scene(self, name: str) -> None:
        self._require()
        self._client.set_current_program_scene(name)  # type: ignore[union-attr]

    def _require(self) -> None:
        if self._client is None:
            raise RuntimeError("OBS 未连接")

"""机台监控：维护各机台的 OBS 连接，按需并行抓图识别分数。

- 状态识别模型（9876）已弃用：不再逐帧轮询机台画面，也不再用状态机
  自动触发抓分；抓分由比赛页面的按钮手动触发。
- 每个机台拥有独立的 OBS WebSocket 连接，首次抓分时惰性建立；
- `capture_scores` 对多台机台并行执行「截图 → 分数识别（9877）」，
  返回每台机台的识别结果与成绩截图字节（JPEG，回退 PNG）；
- 分数服务返回键为 `1pscore`/`2pscore`（无下划线），BP 判定回合读取
  `1pbp`/`2pbp`（miss count）。
"""

from __future__ import annotations

import io
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any

MONOREPO_ROOT = Path(__file__).resolve().parents[3]
if str(MONOREPO_ROOT) not in sys.path:
    sys.path.insert(0, str(MONOREPO_ROOT))

try:  # 兄弟模块，靠 sys.path 引入；缺失时 start() 报错而不是 import 时炸
    from obs_manager.obs_manager import OBSManager
except Exception:  # pragma: no cover - 环境缺依赖时才触发
    OBSManager = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

DEFAULT_MACHINES = {f"IIDX#{i}": f"IIDX#{i}" for i in range(1, 5)}


class CabinetMonitor:
    """维护各机台 OBS 连接；`capture_scores` 并行抓图识别分数。"""

    def __init__(
        self,
        obs_host: str = "localhost",
        obs_port: int = 4455,
        obs_password: str | None = None,
        machines: dict[str, str] | None = None,  # machine_id -> OBS 源名
        interval: float = 1.0,  # 保留兼容旧调用，不再使用
    ) -> None:
        self.obs_host = obs_host
        self.obs_port = obs_port
        self.obs_password = obs_password
        self.machines = dict(machines or DEFAULT_MACHINES)
        self._started = False
        self._obs_managers: dict[str, Any] = {}
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self._started

    def start(self) -> None:
        if OBSManager is None:
            raise RuntimeError("obs_manager 不可用（monorepo 布局或依赖缺失）")
        self._started = True

    def update_credentials(self, host: str, port: int, password: str | None) -> None:
        """同步最新 OBS 连接参数（密码可能在监控启动后才在设置页录入）。"""
        self.obs_host = host
        self.obs_port = port
        self.obs_password = password

    def stop(self) -> None:
        self._started = False
        with self._lock:
            managers = list(self._obs_managers.values())
            self._obs_managers.clear()
        for mgr in managers:
            try:
                mgr.disconnect()
            except Exception:
                logger.exception("断开 OBS 连接失败")

    def capture_scores(self, machine_ids: list[str]) -> dict[str, dict[str, Any]]:
        """并行抓取多台机台的成绩画面并识别分数。

        返回 {machine_id: {"scores": dict, "frame": PNG bytes}}；
        失败的机台返回 {machine_id: {"error": str}}。
        """
        results: dict[str, dict[str, Any]] = {}
        threads = []
        for machine_id in machine_ids:
            if machine_id not in self.machines:
                results[machine_id] = {"error": f"机台 '{machine_id}' 未配置"}
                continue
            t = threading.Thread(
                target=self._capture_one,
                args=(machine_id, results),
                name=f"score-capture-{machine_id}",
                daemon=True,
            )
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        return results

    # ---- 内部 ----

    def _capture_one(self, machine_id: str, results: dict[str, dict[str, Any]]) -> None:
        t0 = time.perf_counter()
        try:
            mgr = self._ensure_obs_manager(machine_id)
            scores = mgr.capture_and_recognize_score(self.machines[machine_id])
            # 优先复用 OBS 返回的原始 JPEG 字节存档；取不到时回退 PIL PNG 编码
            frame = getattr(mgr, "last_score_frame_bytes", None)
            frame_ext = ".jpg"
            if frame is None:
                score_frame = getattr(mgr, "last_score_frame", None)
                frame_ext = ".png"
                if score_frame is not None:
                    buffer = io.BytesIO()
                    score_frame.save(buffer, format="PNG")
                    frame = buffer.getvalue()
            results[machine_id] = {"scores": scores, "frame": frame, "frame_ext": frame_ext}
            logger.info(
                "机台 %s 抓分完成，总耗时 %.0fms", machine_id, (time.perf_counter() - t0) * 1000
            )
        except Exception as exc:
            logger.warning("机台 %s 抓分失败: %s", machine_id, exc)
            results[machine_id] = {"error": str(exc)}

    def _ensure_obs_manager(self, machine_id: str) -> Any:
        with self._lock:
            mgr = self._obs_managers.get(machine_id)
            if mgr is None:
                mgr = OBSManager(
                    host=self.obs_host,
                    port=self.obs_port,
                    password=self.obs_password,
                )
                mgr.connect()
                self._obs_managers[machine_id] = mgr
            return mgr

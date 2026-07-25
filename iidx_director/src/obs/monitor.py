"""机台监控：复用 obs_manager.OBSManager 轮询各机台画面。

- 状态机配置文件锚定 monorepo 根解析，不依赖 cwd；
- 分数服务返回键为 `1pscore`/`2pscore`（无下划线），不要照抄旧
  iidx_tpl_manager 的 `1p_score` 写法；
- 抓分回调只在 process_frame 返回 scores 时触发（状态机 get_score 动作）。
"""

from __future__ import annotations

import logging
import io
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

MONOREPO_ROOT = Path(__file__).resolve().parents[3]
if str(MONOREPO_ROOT) not in sys.path:
    sys.path.insert(0, str(MONOREPO_ROOT))

DEFAULT_STATE_MACHINE_CONFIG = MONOREPO_ROOT / "iidx_state_machine" / "state_machine.yaml"

try:  # 兄弟模块，靠 sys.path 引入；缺失时 start() 报错而不是 import 时炸
    from obs_manager.obs_manager import OBSManager
except Exception:  # pragma: no cover - 环境缺依赖时才触发
    OBSManager = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

DEFAULT_MACHINES = {f"IIDX#{i}": f"IIDX#{i}" for i in range(1, 5)}


class CabinetMonitor:
    """daemon 线程轮询机台；回调由调用方（app 层）提供。"""

    def __init__(
        self,
        obs_host: str = "localhost",
        obs_port: int = 4455,
        obs_password: str | None = None,
        machines: dict[str, str] | None = None,  # machine_id -> OBS 源名
        interval: float = 1.0,
        state_machine_config: Path = DEFAULT_STATE_MACHINE_CONFIG,
        on_scores: Callable[[str, dict[str, Any]], None] | None = None,
        on_update: Callable[[dict[str, Any]], None] | None = None,
        on_score_frame: Callable[[str, bytes], None] | None = None,
    ) -> None:
        self.obs_host = obs_host
        self.obs_port = obs_port
        self.obs_password = obs_password
        self.machines = dict(machines or DEFAULT_MACHINES)
        self.interval = max(0.1, interval)
        self.state_machine_config = state_machine_config
        self.on_scores = on_scores
        self.on_update = on_update
        self.on_score_frame = on_score_frame
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._obs_manager: Any = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        if OBSManager is None:
            raise RuntimeError("obs_manager 不可用（monorepo 布局或依赖缺失）")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="cabinet-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    # ---- 内部 ----

    def _ensure_obs_manager(self) -> Any:
        if self._obs_manager is None:
            mgr = OBSManager(host=self.obs_host, port=self.obs_port, password=self.obs_password)
            mgr.connect()
            mgr.init_state_machine(str(self.state_machine_config), simple_mode=True)
            for machine_id, source_name in self.machines.items():
                mgr.register_machine(machine_id, source_name)
            self._obs_manager = mgr
        return self._obs_manager

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                mgr = self._ensure_obs_manager()
            except Exception as exc:
                logger.warning("OBS 连接失败，5 秒后重试: %s", exc)
                self._obs_manager = None
                self._stop_event.wait(5)
                continue
            for machine_id in self.machines:
                if self._stop_event.is_set():
                    break
                try:
                    result = mgr.process_frame(machine_id)
                except Exception as exc:
                    logger.warning("机台 %s 处理帧失败: %s", machine_id, exc)
                    continue
                if self.on_update is not None:
                    try:
                        self.on_update(result)
                    except Exception:
                        logger.exception("on_update 回调异常")
                scores = result.get("scores")
                if scores and self.on_scores is not None:
                    if self.on_score_frame is not None:
                        try:
                            image = mgr.capture_source(
                                self.machines[machine_id],
                                target_size=(1920, 1080),
                                image_format="png",
                            )
                            buffer = io.BytesIO()
                            image.save(buffer, format="PNG")
                            self.on_score_frame(machine_id, buffer.getvalue())
                        except Exception:
                            logger.exception("机台 %s 成绩截图失败", machine_id)
                    try:
                        self.on_scores(machine_id, scores)
                    except Exception:
                        logger.exception("on_scores 回调异常")
            self._stop_event.wait(self.interval)

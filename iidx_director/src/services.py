"""本地基础服务的生命周期管理。

导播台只负责启动本仓库内可管理的服务。OBS Studio 仍是外部依赖；
状态机则由 ``obs_manager`` 在进程内初始化，不需要单独启动 TCP 服务。
已经占用目标端口的服务视为用户手动启动，导播台不会接管或退出它。
"""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServiceSpec:
    """一个可由导播台管理的本地服务。"""

    name: str
    command: tuple[str, ...]
    cwd: Path
    port: int
    host: str = "127.0.0.1"
    protocol: str = "tcp"


class ServiceStartupError(RuntimeError):
    """基础服务无法启动或在超时时间内未监听端口。"""


def _port_open(host: str, port: int, timeout: float = 0.2) -> bool:
    """检查 TCP 端口是否已经有服务监听。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _websocket_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """用真实 WebSocket 握手探测 relay，避免服务端记录无效 TCP 连接。"""
    try:
        import websockets
    except ImportError:
        return False
    try:
        from websockets.sync.client import connect
        with connect(f"ws://{host}:{port}", open_timeout=timeout):
            return True
    except ImportError:
        return _port_open(host, port, timeout)
    except (OSError, TimeoutError, websockets.WebSocketException):
        return False


def _service_ready(spec: ServiceSpec) -> bool:
    if spec.protocol == "websocket":
        return _websocket_open(spec.host, spec.port)
    return _port_open(spec.host, spec.port)


def default_service_specs(monorepo_root: Path) -> tuple[ServiceSpec, ...]:
    """返回当前 monorepo 布局下的默认基础服务。"""
    state_root = monorepo_root / "iidx_state_reco"
    score_root = monorepo_root / "iidx_score_reco"
    director_root = monorepo_root / "iidx_director"
    return (
        ServiceSpec(
            "state-reco",
            (
                sys.executable,
                str(state_root / "serve.py"),
                "--model",
                str(state_root / "classifier.onnx"),
                "--tcp",
                "9876",
            ),
            state_root,
            9876,
        ),
        ServiceSpec(
            "score-reco",
            (
                sys.executable,
                str(score_root / "serve.py"),
                "--font",
                str(score_root / "font"),
                "--port",
                "9877",
                "--rois-csv",
                str(score_root / "rois.csv"),
                "--image-size",
                "1920,1080",
            ),
            score_root,
            9877,
        ),
        ServiceSpec(
            "bpl-scoreboard",
            (sys.executable, str(monorepo_root / "iidx_bpl_scoreboard" / "server.py")),
            monorepo_root / "iidx_bpl_scoreboard",
            8080,
            host="localhost",
            protocol="websocket",
        ),
        ServiceSpec(
            "knockout-scoreboard",
            (sys.executable, str(monorepo_root / "iidx_knockout_scoreboard" / "server.py")),
            monorepo_root / "iidx_knockout_scoreboard",
            8081,
            host="localhost",
            protocol="websocket",
        ),
        ServiceSpec(
            "sceneinfo",
            (sys.executable, str(director_root / "sceneinfo" / "server.py")),
            director_root,
            8082,
            host="localhost",
            protocol="websocket",
        ),
    )


class DependencyManager:
    """启动并回收导播台依赖的本地服务。"""

    def __init__(
        self,
        monorepo_root: Path,
        specs: tuple[ServiceSpec, ...] | None = None,
        startup_timeout: float = 20.0,
    ) -> None:
        self.specs = specs or default_service_specs(monorepo_root)
        self.startup_timeout = max(0.5, startup_timeout)
        self._owned: dict[str, subprocess.Popen] = {}

    @property
    def owned_processes(self) -> dict[str, subprocess.Popen]:
        """当前由本管理器创建的进程（只读副本）。"""
        return dict(self._owned)

    def start(self) -> None:
        """按顺序启动未运行的服务；任一服务失败则回收本次已启动的进程。"""
        try:
            for spec in self.specs:
                # 外部 relay 可能由另一个事件循环提供服务；已有监听端口直接复用，
                # 不额外发起握手，避免阻塞对方事件循环。
                if _port_open(spec.host, spec.port):
                    logger.info("复用已运行服务 %s (%s:%s)", spec.name, spec.host, spec.port)
                    continue
                self._start_one(spec)
        except Exception:
            self.stop()
            raise

    def _start_one(self, spec: ServiceSpec) -> None:
        if not spec.cwd.is_dir():
            raise ServiceStartupError(f"服务 {spec.name} 工作目录不存在: {spec.cwd}")
        logger.info("启动服务 %s: %s", spec.name, " ".join(spec.command))
        try:
            process = subprocess.Popen(
                list(spec.command),
                cwd=str(spec.cwd),
                stdin=subprocess.DEVNULL,
                start_new_session=(os.name != "nt"),
            )
        except OSError as exc:
            raise ServiceStartupError(f"启动服务 {spec.name} 失败: {exc}") from exc
        self._owned[spec.name] = process

        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if _service_ready(spec):
                logger.info("服务 %s 已就绪 (%s:%s)", spec.name, spec.host, spec.port)
                return
            returncode = process.poll()
            if returncode is not None:
                raise ServiceStartupError(f"服务 {spec.name} 提前退出，返回码: {returncode}")
            time.sleep(0.1)
        raise ServiceStartupError(
            f"服务 {spec.name} 启动超时（{spec.host}:{spec.port}，等待 {self.startup_timeout:g}s）"
        )

    def stop(self) -> None:
        """只停止由本管理器启动的进程，不影响外部已有服务。"""
        processes = list(self._owned.items())
        self._owned.clear()
        for name, process in processes:
            if process.poll() is not None:
                continue
            logger.info("停止服务 %s", name)
            process.terminate()
        for name, process in processes:
            if process.poll() is not None:
                continue
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("服务 %s 未及时退出，强制终止", name)
                process.kill()
                process.wait(timeout=2)

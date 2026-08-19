"""串口音频源切换器。

团队赛 1V1 时，根据第一个选手分配的机台自动切换音频输入源。
音频切换设备通过串口接收 1-4 的 ASCII 数字，对应 1-4 号机台输入。
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

try:
    import serial
    import serial.tools.list_ports
except ImportError:  # pragma: no cover - pyserial 为可选依赖
    serial = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_SOURCE_PATTERN = re.compile(r"(\d+)")


def extract_source_number(machine_id: str) -> int | None:
    """从机台 ID 中提取数字编号，例如 IIDX#3 -> 3。"""
    match = _SOURCE_PATTERN.search(machine_id)
    if not match:
        return None
    return int(match.group(1))


def list_serial_ports() -> list[str]:
    """返回本机可用串口设备名列表。未安装 pyserial 时返回空列表。"""
    if serial is None:
        return []
    return [port.device for port in serial.tools.list_ports.comports()]


class SerialAudioSwitcher:
    """通过串口向音频切换设备发送机台编号（1-4）。"""

    def __init__(
        self,
        enabled: bool = False,
        port: str | None = None,
        baudrate: int = 9600,
        timeout: float = 1.0,
    ) -> None:
        self.enabled = enabled
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

    def switch(self, machine_id: str) -> bool:
        """切换到指定机台的音频源。返回是否成功发送。"""
        if not self.enabled:
            logger.debug("串口音频切换未启用，跳过")
            return False
        number = extract_source_number(machine_id)
        if number is None:
            logger.warning("无法从机台 ID %r 提取音频源编号", machine_id)
            return False
        return self.send_number(number)

    def send_number(self, number: int) -> bool:
        """直接发送 1-4 的编号。失败时自动重试一次。"""
        if not self.enabled or not self.port:
            return False
        if serial is None:
            logger.warning("未安装 pyserial，无法发送串口音频切换指令")
            return False
        if number not in (1, 2, 3, 4):
            logger.warning("音频源编号 %d 不在有效范围 1-4 内", number)
            return False
        for attempt in (1, 2):
            try:
                with serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                ) as ser:
                    ser.write(str(number).encode())
                    ser.flush()
                logger.info("已通过 %s 发送音频源切换指令: %d", self.port, number)
                return True
            except serial.SerialException as exc:  # type: ignore[union-attr]
                logger.error(
                    "串口音频切换失败 (%s, 第 %d 次尝试): %s", self.port, attempt, exc
                )
                if attempt == 1:
                    # 端口可能被上次未释放的句柄临时占用，稍等后重试一次
                    time.sleep(0.3)
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "port": self.port,
            "baudrate": self.baudrate,
            "timeout": self.timeout,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SerialAudioSwitcher":
        if not data:
            return cls()
        return cls(
            enabled=bool(data.get("enabled", False)),
            port=data.get("port") or None,
            baudrate=int(data.get("baudrate", 9600)),
            timeout=float(data.get("timeout", 1.0)),
        )

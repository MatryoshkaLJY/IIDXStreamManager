#!/usr/bin/env python3
"""
OBS Manager - 与 OBS Studio 交互的工具类

功能：
1. 连接 OBS WebSocket
2. 抓取指定视频源的图像
3. resize 后发送到推理服务进行识别
4. 抓取高分区域 (1920x1080) 并识别 ROI 中的数字

依赖:
    pip install obsws-python pillow

示例:
    from obs_manager import OBSManager

    obs = OBSManager(host="localhost", port=4455, password="1145141919")
    obs.connect()

    # 功能1: 抓取并识别游戏状态
    result = obs.capture_and_recognize(
        source_name="video",
        target_size=(224, 224),
        infer_addr=("127.0.0.1", 9876)  # 或 Unix socket: "/tmp/iidx_infer.sock"
    )
    print(f"识别结果: {result}")  # 如 "play"

    # 功能2: 抓取高分区域并识别
    results = obs.capture_and_recognize_score(
        source_name="video",
        infer_addr=("127.0.0.1", 9877)
    )
    print(f"高分: {results}")  # 如 {"ROI_1": "1234", ...}
"""

import io
import json
import socket
import struct
from dataclasses import dataclass
from typing import Union, Tuple, Optional, List, Dict, Any
from pathlib import Path

try:
    import obsws_python as obsws
except ImportError:
    raise ImportError("请安装 obsws-python: pip install obsws-python")

try:
    from PIL import Image
except ImportError:
    raise ImportError("请安装 pillow: pip install pillow")


@dataclass
class MachineConfig:
    """Configuration for a single game cabinet."""
    machine_id: str
    source_name: str
    state_infer_addr: Union[str, Tuple[str, int]] = ("127.0.0.1", 9876)
    score_infer_addr: Tuple[str, int] = ("127.0.0.1", 9877)
    # Score validation retry state
    pending_score_validation: bool = False
    last_invalid_scores: Optional[dict] = None


class OBSManager:
    """OBS WebSocket 管理类"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 4455,
        password: Optional[str] = None,
        timeout: int = 5
    ):
        """
        初始化 OBS Manager

        Args:
            host: OBS WebSocket 主机地址
            port: OBS WebSocket 端口
            password: OBS WebSocket 密码（可选）
            timeout: 连接超时时间（秒）
        """
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._client: Optional[obws.ReqClient] = None

        # Multi-machine state tracking
        self.machines: Dict[str, MachineConfig] = {}
        self._state_manager: Optional[Any] = None

    def connect(self) -> None:
        """连接到 OBS WebSocket"""
        try:
            self._client = obsws.ReqClient(
                host=self.host,
                port=self.port,
                password=self.password,
                timeout=self.timeout
            )
            # 测试连接
            version = self._client.get_version()
            print(f"已连接到 OBS {version.obs_version} (WebSocket {version.obs_web_socket_version})")
        except Exception as e:
            raise ConnectionError(f"无法连接到 OBS WebSocket ({self.host}:{self.port}): {e}")

    def disconnect(self) -> None:
        """断开与 OBS 的连接"""
        if self._client:
            self._client = None
            print("已断开 OBS 连接")

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._client is not None

    def _ensure_connected(self) -> None:
        """确保已连接，否则抛出异常"""
        if not self.is_connected():
            raise RuntimeError("未连接到 OBS，请先调用 connect()")

    def get_sources(self) -> list:
        """获取所有可用视频源列表"""
        self._ensure_connected()
        try:
            resp = self._client.get_input_list()
            return [item["inputName"] for item in resp.inputs]
        except Exception as e:
            raise RuntimeError(f"获取视频源列表失败: {e}")

    def capture_source(
        self,
        source_name: str,
        target_size: Optional[Tuple[int, int]] = None,
        image_format: str = "jpeg"
    ) -> Image.Image:
        """
        抓取指定视频源的图像

        Args:
            source_name: 视频源名称（如 "video"）
            target_size: 目标尺寸 (宽, 高)，如 (224, 224)
            image_format: 截图格式（jpeg 或 png）

        Returns:
            PIL Image 对象
        """
        self._ensure_connected()

        try:
            # 获取视频源截图 (obsws-python 5.x API)
            width, height = target_size if target_size else (0, 0)
            resp = self._client.get_source_screenshot(
                name=source_name,
                img_format=image_format.replace("image/", "").replace("jpeg", "jpg"),
                width=width,
                height=height,
                quality=95
            )

            # 解析 base64 图像数据
            import base64
            img_data = resp.image_data
            if img_data.startswith("data:image"):
                # 移除 data URI 前缀
                img_data = img_data.split(",", 1)[1]

            img_bytes = base64.b64decode(img_data)
            img = Image.open(io.BytesIO(img_bytes))

            # 如果需要特定尺寸但 OBS 没有正确返回
            if target_size and img.size != target_size:
                img = img.resize(target_size, Image.BILINEAR)

            return img

        except Exception as e:
            raise RuntimeError(f"抓取视频源 '{source_name}' 失败: {e}")

    @staticmethod
    def _send_to_inference(
        img: Image.Image,
        infer_addr: Union[str, Tuple[str, int]],
        image_format: str = "jpeg"
    ) -> str:
        """
        发送图像到推理服务

        Args:
            img: PIL Image 对象
            infer_addr: 推理服务地址
                       - TCP: ("127.0.0.1", 9876)
                       - Unix socket: "/tmp/iidx_infer.sock"
            image_format: 图像格式

        Returns:
            识别结果标签字符串
        """
        # 将图像转为字节
        buffer = io.BytesIO()
        if image_format.lower() in ("jpg", "jpeg"):
            img.save(buffer, format="JPEG", quality=95)
        else:
            img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        # 准备数据：4字节大端长度 + 图像数据
        data = struct.pack(">I", len(img_bytes)) + img_bytes

        # 创建 socket 连接
        if isinstance(infer_addr, str):
            # Unix socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(infer_addr)
        else:
            # TCP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(infer_addr)

        try:
            # 发送数据
            sock.sendall(data)
            # 接收结果
            response = sock.recv(256).decode().strip()
            return response
        finally:
            sock.close()

    def capture_and_recognize(
        self,
        source_name: str,
        infer_addr: Union[str, Tuple[str, int]] = ("127.0.0.1", 9876),
        target_size: Tuple[int, int] = (224, 224),
        image_format: str = "jpeg"
    ) -> str:
        """
        抓取图像并发送到推理服务识别

        Args:
            source_name: OBS 视频源名称
            infer_addr: 推理服务地址（Unix socket 路径或 TCP (host, port)）
            target_size: 图像目标尺寸
            image_format: 图像格式

        Returns:
            识别结果标签字符串（如 "play"）

        Example:
            # Unix socket 模式
            result = obs.capture_and_recognize(
                source_name="video",
                infer_addr=("127.0.0.1", 9876)
            )

            # Unix socket 模式
            result = obs.capture_and_recognize(
                source_name="video",
                infer_addr="/tmp/iidx_infer.sock"
            )
        """
        # 1. 抓取图像
        img = self.capture_source(source_name, target_size, image_format)

        # 2. 发送到推理服务
        result = self._send_to_inference(img, infer_addr, image_format)

        return result

    def capture_to_file(
        self,
        source_name: str,
        output_path: str,
        target_size: Optional[Tuple[int, int]] = None
    ) -> str:
        """
        抓取图像并保存到文件

        Args:
            source_name: OBS 视频源名称
            output_path: 输出文件路径
            target_size: 目标尺寸

        Returns:
            保存的文件路径
        """
        img = self.capture_source(source_name, target_size)
        img.save(output_path)
        return output_path

    # ========== 高分区域 ROI 识别功能 ==========

    @staticmethod
    def load_rois_from_csv(csv_path: str) -> List[Tuple[str, int, int, int, int]]:
        """
        从 CSV 文件加载 ROI 配置
        格式: name,x1,y1,x2,y2
        返回: List of (name, x1, y1, x2, y2)
        """
        rois = []
        with open(csv_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) >= 5:
                    name = parts[0]
                    x1, y1, x2, y2 = map(int, parts[1:5])
                    rois.append((name, x1, y1, x2, y2))
        return rois

    def capture_and_recognize_score(
        self,
        source_name: str,
        infer_addr: Tuple[str, int] = ("127.0.0.1", 9877),
        target_size: Tuple[int, int] = (1920, 1080),
        rois: Optional[List[Tuple[str, int, int, int, int]]] = None
    ) -> dict:
        """
        抓取高分区域图像并识别 ROI 中的数字

        Args:
            source_name: OBS 视频源名称
            infer_addr: 分数识别服务地址 (host, port)
            target_size: 图像目标尺寸 (默认 1920x1080)
            rois: ROI 区域列表，格式为 [(name, x1, y1, x2, y2), ...]
                  如果为 None，则假设服务已配置 ROI

        Returns:
            字典，如 {"2pbscore": "1234", "2pscore": "5678", ...}

        Example:
            with OBSManager() as obs:
                # 从 CSV 加载 ROI
                rois = OBSManager.load_rois_from_csv("rois.csv")
                results = obs.capture_and_recognize_score(
                    source_name="video",
                    infer_addr=("127.0.0.1", 9877),
                    rois=rois
                )
                print(f"2P 分数: {results['2pscore']}")
        """
        # 1. 抓取 1920x1080 图像
        img = self.capture_source(source_name, target_size, image_format="png")

        # 2. 转换为字节
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        # 3. 发送到分数识别服务
        # 协议: [4字节大端长度] [PNG图像数据]
        data = struct.pack(">I", len(img_bytes)) + img_bytes

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(infer_addr)

        try:
            sock.sendall(data)
            # 接收 JSON 结果
            response = sock.recv(4096).decode().strip()
            results = json.loads(response)
            return results
        finally:
            sock.close()

    def capture_score_regions(
        self,
        source_name: str,
        output_dir: Optional[str] = None,
        target_size: Tuple[int, int] = (1920, 1080),
        rois: Optional[List[Tuple[str, int, int, int, int]]] = None
    ) -> dict:
        """
        抓取高分区域并裁剪出各个 ROI 保存

        Args:
            source_name: OBS 视频源名称
            output_dir: ROI 图像保存目录 (None 则不保存)
            target_size: 图像目标尺寸 (默认 1920x1080)
            rois: ROI 区域列表，格式为 [(name, x1, y1, x2, y2), ...]

        Returns:
            字典，包含完整图像和各个 ROI 的 PIL Image 对象
            {
                "full": PIL.Image,
                "2pbscore": PIL.Image,
                "2pscore": PIL.Image,
                ...
            }
        """
        # 抓取完整图像
        full_img = self.capture_source(source_name, target_size, image_format="png")

        results = {"full": full_img}

        if rois is None:
            return results

        # 裁剪各个 ROI
        for roi in rois:
            name, x1, y1, x2, y2 = roi
            # 确保坐标在图像范围内
            w, h = full_img.size
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            roi_img = full_img.crop((x1, y1, x2, y2))
            results[name] = roi_img

            # 保存到文件
            if output_dir:
                output_path = Path(output_dir) / f"{name}.png"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                roi_img.save(output_path)
                print(f"保存 {name}: {output_path}")

        return results

    # ========== 多机器状态机集成 ==========

    def _import_state_machine_manager(self):
        """延迟导入 IIDXStateMachineManager，支持同级目录结构。"""
        try:
            from iidx_state_machine.state_machine import IIDXStateMachineManager
            return IIDXStateMachineManager
        except ImportError as e:
            import sys
            import os
            parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if parent not in sys.path:
                sys.path.insert(0, parent)
            try:
                from iidx_state_machine.state_machine import IIDXStateMachineManager
                return IIDXStateMachineManager
            except ImportError:
                raise ImportError(
                    "无法导入 iidx_state_machine。请确保项目根目录在 PYTHONPATH 中。"
                ) from e

    def init_state_machine(
        self,
        config_path: str,
        log_level: str = "INFO",
        simple_mode: bool = False
    ) -> None:
        """初始化多机器状态机管理器。

        Args:
            config_path: 状态机 YAML 配置文件路径
            log_level: 日志级别
            simple_mode: 是否启用简化输出
        """
        IIDXStateMachineManager = self._import_state_machine_manager()
        self._state_manager = IIDXStateMachineManager(
            config_path, log_level, simple_mode
        )

    def register_machine(
        self,
        machine_id: str,
        source_name: str,
        state_infer_addr: Union[str, Tuple[str, int]] = ("127.0.0.1", 9876),
        score_infer_addr: Tuple[str, int] = ("127.0.0.1", 9877)
    ) -> None:
        """注册一台游戏机。

        Args:
            machine_id: 机器唯一标识
            source_name: OBS 视频源名称
            state_infer_addr: 状态识别服务地址
            score_infer_addr: 分数识别服务地址
        """
        self.machines[machine_id] = MachineConfig(
            machine_id=machine_id,
            source_name=source_name,
            state_infer_addr=state_infer_addr,
            score_infer_addr=score_infer_addr,
        )
        if self._state_manager is not None:
            self._state_manager.add_machine(machine_id)

    def process_frame(self, machine_id: str) -> Dict[str, Any]:
        """处理单台机器的单帧。

        流程:
        1. 抓取图像并进行状态识别
        2. 将识别结果输入状态机
        3. 若状态机触发 get_score，则抓取分数
        4. 验证分数合法性，不合法且在 score 状态时重试

        Args:
            machine_id: 机器唯一标识

        Returns:
            包含 machine_id、识别标签、状态结果、分数的字典
        """
        if machine_id not in self.machines:
            raise ValueError(f"机器 '{machine_id}' 未注册")
        if self._state_manager is None:
            raise RuntimeError(
                "状态机未初始化，请先调用 init_state_machine()"
            )

        cfg = self.machines[machine_id]

        # 1. 状态识别
        label = self.capture_and_recognize(
            cfg.source_name, cfg.state_infer_addr
        )

        # 2. 状态机处理
        state_result = self._state_manager.process_event(machine_id, label)

        # 3. 分数识别（仅在进入 SCORE 状态时触发，或需要重试时）
        scores = None
        need_score_capture = (
            state_result and "get_score" in state_result.get("actions_triggered", [])
        ) or (
            cfg.pending_score_validation and label == "score"
        )

        if need_score_capture:
            scores = self.capture_and_recognize_score(
                cfg.source_name, cfg.score_infer_addr
            )

            # 4. 验证分数合法性
            if scores:
                p1_valid = scores.get("1p_valid")
                p2_valid = scores.get("2p_valid")

                # 如果其中有一个为 true，表明识别正常
                if p1_valid is True or p2_valid is True:
                    cfg.pending_score_validation = False
                    cfg.last_invalid_scores = None
                else:
                    # 识别不正常，标记需要重试
                    cfg.pending_score_validation = True
                    cfg.last_invalid_scores = scores

                    # 如果当前已经不是 score 状态，放弃重试
                    if label != "score":
                        cfg.pending_score_validation = False
                        # 返回最后一次无效的分数（带有验证标记）
                        scores = cfg.last_invalid_scores

        return {
            "machine_id": machine_id,
            "timestamp": state_result.get("timestamp") if state_result else None,
            "label": label,
            "state": state_result,
            "scores": scores,
            "score_validation_pending": cfg.pending_score_validation,
        }

    def run(self, interval: float = 1.0) -> None:
        """循环轮询所有注册的游戏机。

        Args:
            interval: 每台机器之间的轮询间隔（秒）
        """
        if not self.machines:
            print("没有注册的游戏机")
            return

        import time
        print(f"开始轮询 {len(self.machines)} 台游戏机，间隔 {interval}s")
        print(f"注册机器: {list(self.machines.keys())}")
        try:
            while True:
                for machine_id in self.machines:
                    result = self.process_frame(machine_id)
                    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
                time.sleep(interval)
        except KeyboardInterrupt:
            print("轮询已停止")


def main():
    """命令行示例"""
    import argparse

    parser = argparse.ArgumentParser(description="OBS 图像抓取与识别")
    parser.add_argument("--host", default="localhost", help="OBS WebSocket 主机")
    parser.add_argument("--port", type=int, default=4455, help="OBS WebSocket 端口")
    parser.add_argument("--password", default=None, help="OBS WebSocket 密码")
    parser.add_argument("--source", default="video", help="视频源名称")
    parser.add_argument("--infer-sock", default=None,
                        help="推理服务 Unix socket 路径（优先于 TCP）")
    parser.add_argument("--infer-tcp", type=int, default=9876,
                        help="推理服务 TCP 端口")
    parser.add_argument("--size", type=int, nargs=2, default=[224, 224],
                        help="目标尺寸 (宽 高)")
    parser.add_argument("--output", "-o", default=None,
                        help="同时保存截图到文件")

    args = parser.parse_args()

    # 确定推理服务地址
    if args.infer_sock:
        infer_addr = args.infer_sock
    else:
        infer_addr = ("127.0.0.1", args.infer_tcp)

    # 使用上下文管理器
    with OBSManager(host=args.host, port=args.port, password=args.password) as obs:
        print(f"视频源列表: {obs.get_sources()}")

        # 抓取并识别
        print(f"\n正在从 '{args.source}' 抓取图像并识别...")
        result = obs.capture_and_recognize(
            source_name=args.source,
            infer_addr=infer_addr,
            target_size=tuple(args.size)
        )
        print(f"识别结果: {result}")

        # 可选保存
        if args.output:
            obs.capture_to_file(args.source, args.output, tuple(args.size))
            print(f"截图已保存: {args.output}")


if __name__ == "__main__":
    main()

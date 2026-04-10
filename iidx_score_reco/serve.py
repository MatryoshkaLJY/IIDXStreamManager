#!/usr/bin/env python3
"""
IIDX 分数识别推理服务
支持 TCP 传输，接收图像字节，识别指定 ROI 区域的数字

协议（每次请求）:
  发送: [4字节大端无符号整数 = 图片长度] [图片字节 (JPEG/PNG/...)]
  接收: [JSON字符串\n]  例如 {"ROI_1": "1234", "ROI_2": "5678", ...}

用法:
  python3 serve.py --font font/ --port 9877      # TCP 模式 (默认端口 9877)
  python3 serve.py --font font/ --rois "1547,488,1700,517;1547,549,1700,581"  # 自定义ROI

依赖: pip install opencv-python numpy
"""

import argparse
import io
import json
import socket
import struct
import sys
import threading
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image

# 导入识别器
from recognizer import IIDXDigitRecognizer

# 获取当前文件所在目录
SCRIPT_DIR = Path(__file__).parent.resolve()

# 默认的4个ROI坐标 (从 test.py 获取)
DEFAULT_ROIS = [
    ((1547, 488), (1700, 517)),  # 右上1
    ((1547, 549), (1700, 581)),  # 右上2
    ((1400, 488), (1547, 517)),  # 左上1
    ((1400, 549), (1547, 581)),  # 左上2
]


def parse_rois(roi_string: str) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """
    解析 ROI 字符串
    格式: "x1,y1,x2,y2;x1,y1,x2,y2;..."
    例如: "1547,488,1700,517;1547,549,1700,581"
    """
    rois = []
    for roi_part in roi_string.split(';'):
        coords = list(map(int, roi_part.split(',')))
        if len(coords) != 4:
            raise ValueError(f"无效的 ROI 格式: {roi_part}")
        rois.append(((coords[0], coords[1]), (coords[2], coords[3])))
    return rois


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


def validate_score_result(results: dict) -> dict:
    """
    验证1P和2P的分数是否符合公式：
    - 1pscore = 2 * 1ppg + 1pgr
    - 2pscore = 2 * 2ppg + 2pgr

    返回包含验证状态的额外字段
    """
    validated = dict(results)

    def parse_int(value):
        """解析整数字符串，处理空值或无效值"""
        if not value or value == "":
            return None
        try:
            return int(value)
        except ValueError:
            return None

    # 验证1P
    p1_score = parse_int(results.get("1pscore"))
    p1_pg = parse_int(results.get("1ppg"))
    p1_gr = parse_int(results.get("1pgr"))

    if p1_score is not None and p1_pg is not None and p1_gr is not None:
        expected = 2 * p1_pg + p1_gr
        validated["1p_valid"] = (p1_score == expected)
        validated["1p_expected"] = str(expected)
    else:
        validated["1p_valid"] = None  # 缺少字段无法验证

    # 验证2P
    p2_score = parse_int(results.get("2pscore"))
    p2_pg = parse_int(results.get("2ppg"))
    p2_gr = parse_int(results.get("2pgr"))

    if p2_score is not None and p2_pg is not None and p2_gr is not None:
        expected = 2 * p2_pg + p2_gr
        validated["2p_valid"] = (p2_score == expected)
        validated["2p_expected"] = str(expected)
    else:
        validated["2p_valid"] = None  # 缺少字段无法验证

    return validated


def recv_exact(conn: socket.socket, n: int) -> bytes:
    """精确接收 n 字节数据"""
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("连接关闭")
        buf.extend(chunk)
    return bytes(buf)


def handle_client(
    conn: socket.socket,
    addr,
    recognizer: IIDXDigitRecognizer,
    rois: List[Tuple[str, int, int, int, int]],
    target_size: Tuple[int, int]
):
    """处理客户端连接"""
    try:
        while True:
            # 读取长度头
            header = recv_exact(conn, 4)
            length = struct.unpack(">I", header)[0]
            if length == 0:
                break

            # 读取图像数据
            img_bytes = recv_exact(conn, length)

            # 转换为 PIL Image
            img = Image.open(io.BytesIO(img_bytes))
            # 转换为 RGB (如果是 RGBA 或其他模式)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 检查图像尺寸，如果需要则缩放
            current_width, current_height = img.size
            target_width, target_height = target_size

            if (current_width, current_height) != (target_width, target_height):
                # 图像尺寸不匹配，进行缩放
                print(f"[调试] 图像尺寸 {current_width}x{current_height} 与目标 {target_width}x{target_height} 不匹配，进行缩放")
                img = img.resize((target_width, target_height), Image.LANCZOS)

            # 保存为临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
                img.save(tmp_path)

            try:
                # 识别所有 ROI
                results = recognizer.recognize_all_rois(tmp_path, rois, debug=False)
            finally:
                # 清理临时文件
                Path(tmp_path).unlink(missing_ok=True)

            # 验证1P和2P分数的合法性
            validated_results = validate_score_result(results)

            # 发送 JSON 结果
            response = json.dumps(validated_results) + "\n"
            conn.sendall(response.encode())

    except (ConnectionError, ConnectionResetError):
        pass
    except Exception as e:
        print(f"[错误] {addr}: {e}", file=sys.stderr)
        try:
            error_response = json.dumps({"error": str(e)}) + "\n"
            conn.sendall(error_response.encode())
        except:
            pass
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="IIDX 分数识别推理服务")
    parser.add_argument("--font", default="font", help="字体模板目录路径")
    parser.add_argument("--port", type=int, default=9877, help="TCP 端口 (默认: 9877)")
    parser.add_argument("--host", default="127.0.0.1", help="绑定地址 (默认: 127.0.0.1)")
    parser.add_argument("--rois", default=None,
                        help="自定义 ROI，格式: 'x1,y1,x2,y2;x1,y1,x2,y2' (默认使用4个标准ROI)")
    parser.add_argument("--rois-csv", default=None,
                        help="从 CSV 文件加载 ROI 配置 (格式: name,x1,y1,x2,y2)")
    parser.add_argument("--image-size", type=str, default="1920,1080",
                        help="期望的图像尺寸 (默认: 1920,1080)")
    args = parser.parse_args()

    # 解析字体目录（相对于脚本目录）
    font_dir = Path(args.font)
    if not font_dir.is_absolute():
        font_dir = SCRIPT_DIR / font_dir

    # 加载识别器
    print(f"加载字体模板从: {font_dir}")
    recognizer = IIDXDigitRecognizer(str(font_dir))

    # 解析 ROI
    if args.rois_csv:
        rois = load_rois_from_csv(args.rois_csv)
        print(f"从 CSV 加载 ROI: {len(rois)} 个区域")
        for roi in rois:
            print(f"  {roi[0]}: ({roi[1]},{roi[2]})-({roi[3]},{roi[4]})")
    elif args.rois:
        # 旧的格式解析
        rois = []
        for roi_part in args.rois.split(';'):
            coords = list(map(int, roi_part.split(',')))
            if len(coords) != 4:
                raise ValueError(f"无效的 ROI 格式: {roi_part}")
            rois.append((f"roi_{len(rois)+1}", coords[0], coords[1], coords[2], coords[3]))
        print(f"使用自定义 ROI: {rois}")
    else:
        # 使用默认 ROI (转换为新格式)
        rois = [(f"ROI_{i+1}", x1, y1, x2, y2)
                for i, ((x1, y1), (x2, y2)) in enumerate(DEFAULT_ROIS)]
        print(f"使用默认 ROI: {rois}")

    # 解析期望的图像尺寸
    image_width, image_height = map(int, args.image_size.split(','))
    print(f"期望图像尺寸: {image_width}x{image_height}")

    # 创建 TCP 服务器
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((args.host, args.port))
    server.listen(8)

    print(f"服务启动，监听: tcp://{args.host}:{args.port}")
    print("按 Ctrl+C 停止")

    try:
        while True:
            conn, addr = server.accept()
            print(f"[连接] {addr}")
            t = threading.Thread(
                target=handle_client,
                args=(conn, addr, recognizer, rois, (image_width, image_height)),
                daemon=True
            )
            t.start()
    except KeyboardInterrupt:
        print("\n正在停止...")
    finally:
        server.close()


if __name__ == "__main__":
    main()

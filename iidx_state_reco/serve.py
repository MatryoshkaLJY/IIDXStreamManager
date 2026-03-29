#!/usr/bin/env python3
"""
推理服务：监听 Unix socket 或 TCP，接收图片字节，返回分类结果。

协议（每次请求）：
  发送: [4字节大端无符号整数 = 图片长度] [图片字节 (JPEG/PNG/...)]
  接收: [标签字符串\n]  例如 "play\n"

用法：
  python3 serve.py --model classifier.onnx               # Unix socket: /tmp/iidx_infer.sock
  python3 serve.py --model classifier.onnx --tcp 9876    # TCP 127.0.0.1:9876
  python3 serve.py --model classifier.onnx --sock /run/iidx.sock

测试（需要 socat）：
  # Unix socket
  ( printf "\\x00\\x00\\x1a\\x2b"; cat frame.jpg ) | socat - UNIX-CONNECT:/tmp/iidx_infer.sock

依赖: pip install onnxruntime pillow  (GPU: pip install onnxruntime-gpu)
"""

import argparse
import io
import socket
import struct
import sys
import threading
from pathlib import Path

import numpy as np
from PIL import Image

# 预加载 PyTorch 附带的 CUDA 12 库，供 onnxruntime-gpu 的 CUDA provider 使用
import ctypes as _ctypes, glob as _glob
for _site in sys.path:
    if "site-packages" not in _site:
        continue
    _libs = _glob.glob(f"{_site}/nvidia/*/lib/lib*.so.*")
    if not _libs:
        continue
    for _so in _libs:
        try:
            _ctypes.CDLL(_so, mode=_ctypes.RTLD_GLOBAL)
        except OSError:
            pass
    break

MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def load_labels(labels_path: str) -> list[str]:
    labels = {}
    with open(labels_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            idx, name = line.split("\t", 1)
            labels[int(idx)] = name
    return [labels[i] for i in range(len(labels))]


def preprocess(img: Image.Image) -> np.ndarray:
    img = img.convert("RGB").resize((224, 224), Image.BILINEAR)
    x = np.array(img, dtype=np.float32) / 255.0
    x = (x - MEAN) / STD
    return x.transpose(2, 0, 1)[np.newaxis]  # NCHW


def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def recv_exact(conn: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("连接关闭")
        buf.extend(chunk)
    return bytes(buf)


def handle_client(conn: socket.socket, addr, sess, input_name: str, labels: list[str]):
    try:
        while True:
            # 读取长度头
            header = recv_exact(conn, 4)
            length = struct.unpack(">I", header)[0]
            if length == 0:
                break
            img_bytes = recv_exact(conn, length)
            img = Image.open(io.BytesIO(img_bytes))
            x = preprocess(img)
            logits = sess.run(None, {input_name: x})[0][0]
            probs = softmax(logits)
            label = labels[probs.argmax()]
            conn.sendall((label + "\n").encode())
    except (ConnectionError, ConnectionResetError):
        pass
    except Exception as e:
        print(f"[错误] {addr}: {e}", file=sys.stderr)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="IIDX 状态识别推理服务")
    parser.add_argument("--model", default="classifier.onnx", help="ONNX 模型路径")
    parser.add_argument("--labels", default=None, help="标签文件（默认同模型名.labels.txt）")
    parser.add_argument("--sock", default="/tmp/iidx_infer.sock", help="Unix socket 路径")
    parser.add_argument("--tcp", type=int, default=None, metavar="PORT",
                        help="改用 TCP，指定端口（如 9876）")
    args = parser.parse_args()

    import onnxruntime as ort

    labels_path = args.labels or str(Path(args.model).with_suffix(".labels.txt"))
    labels = load_labels(labels_path)

    available = ort.get_available_providers()
    providers = (["CUDAExecutionProvider", "CPUExecutionProvider"]
                 if "CUDAExecutionProvider" in available else ["CPUExecutionProvider"])
    sess = ort.InferenceSession(args.model, providers=providers)
    input_name = sess.get_inputs()[0].name
    provider = sess.get_providers()[0]
    print(f"模型加载完成，{len(labels)} 类，后端: {provider}", flush=True)

    if args.tcp is not None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", args.tcp))
        addr_str = f"tcp://127.0.0.1:{args.tcp}"
    else:
        sock_path = Path(args.sock)
        if sock_path.exists():
            sock_path.unlink()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(sock_path))
        addr_str = f"unix://{sock_path}"

    server.listen(8)
    print(f"监听中: {addr_str}", flush=True)

    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client,
                                 args=(conn, addr, sess, input_name, labels),
                                 daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n退出", file=sys.stderr)
    finally:
        server.close()
        if args.tcp is None:
            Path(args.sock).unlink(missing_ok=True)


if __name__ == "__main__":
    main()

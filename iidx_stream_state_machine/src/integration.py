"""与 iidx_state_reco 识别的集成示例"""

import struct
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from state_machine import IIDXStateMachine


def demo_with_recognition_service():
    """
    演示：从 iidx_state_reco 的 serve.py 接收识别结果

    需要先启动识别服务:
        cd ../iidx_state_reco && python3 serve.py --model classifier.onnx
    """
    import socket

    sm = IIDXStateMachine()

    SOCK_PATH = "/tmp/iidx_infer.sock"

    print(f"Connecting to recognition service at {SOCK_PATH}...")
    print("请向 /tmp/iidx_infer.sock 发送图像数据")
    print("按 Ctrl+C 退出\n")

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.bind("/tmp/iidx_state_machine.sock")
            s.listen(1)

            while True:
                conn, addr = s.accept()
                with conn:
                    data = conn.recv(1024)
                    if data:
                        recognized = data.decode().strip()
                        current_state = sm.feed(recognized)
                        conn.sendall(f"ACK: {current_state.value}\n".encode())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")


def simulate_from_recognition_log():
    """
    演示：从识别日志模拟状态流转

    模拟 infer_onnx.py 的输出格式处理
    """
    print("模拟从识别结果构建状态流转")
    print("-" * 50)

    sm = IIDXStateMachine()

    # 模拟识别日志（通常是 1fps 的识别结果）
    recognition_log = [
        "idle", "idle", "idle",
        "interlude", "interlude",
        "entry", "entry",
        "interlude", "interlude",
        "modesel", "modesel",
        "pay", "pay",
        "interlude", "interlude",
        "songsel", "songsel", "songsel",
        "confirm", "confirm",
        "play", "play", "play", "play", "play",
        "score", "score",
        "interlude", "interlude",
        "entry", "entry",
    ]

    for i, recognized in enumerate(recognition_log):
        prev_state = sm.state
        current = sm.feed(recognized)
        if prev_state != current:
            print(f"[{i:3}] {recognized:12} -> STATE CHANGED: {current.value}")
        else:
            print(f"[{i:3}] {recognized:12}    (debouncing...)")

    print("-" * 50)
    print("Status:", sm.get_status())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", action="store_true", help="模拟识别日志")
    parser.add_argument("--service", action="store_true", help="连接识别服务")
    args = parser.parse_args()

    if args.service:
        demo_with_recognition_service()
    else:
        simulate_from_recognition_log()

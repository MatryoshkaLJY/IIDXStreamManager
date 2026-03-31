#!/usr/bin/env python3
"""
obs_manager 测试脚本

两种测试模式:
1. 模拟测试 (默认): 模拟 OBS 和推理服务，验证代码逻辑
2. 实际测试: 连接真实的 OBS 和推理服务

用法:
    python3 test_obs_manager.py          # 模拟测试
    python3 test_obs_manager.py --real   # 实际测试（需要 OBS 和 serve.py 运行）
"""

import sys
import os
import time
import struct
import socket
import threading
import io
import base64
from unittest.mock import Mock, patch

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
import numpy as np


def create_test_image(width: int = 224, height: int = 224, color: tuple = (100, 150, 200)) -> Image.Image:
    """创建测试图像"""
    img = Image.new('RGB', (width, height), color)
    return img


def create_mock_obs_response(img: Image.Image) -> str:
    """创建模拟的 OBS 截图响应 (base64 data URI)"""
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()
    b64_data = base64.b64encode(img_bytes).decode('utf-8')
    return f"data:image/png;base64,{b64_data}"


class MockInferenceServer:
    """模拟推理服务 (类似 serve.py 的行为)"""

    def __init__(self, socket_path: str = "/tmp/test_iidx_infer.sock", response_label: str = "play"):
        self.socket_path = socket_path
        self.response_label = response_label
        self.server = None
        self.thread = None
        self.running = False

    def start(self):
        """启动模拟推理服务"""
        import socket as sock_module

        # 清理旧 socket
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        self.server = sock_module.socket(sock_module.AF_UNIX, sock_module.SOCK_STREAM)
        self.server.bind(self.socket_path)
        self.server.listen(5)
        self.running = True

        def handle_client(conn, addr):
            try:
                while self.running:
                    # 读取 4 字节长度头
                    header = conn.recv(4)
                    if not header or len(header) < 4:
                        break
                    length = struct.unpack(">I", header)[0]
                    if length == 0:
                        break

                    # 读取图像数据
                    img_data = b""
                    while len(img_data) < length:
                        chunk = conn.recv(length - len(img_data))
                        if not chunk:
                            break
                        img_data += chunk

                    # 模拟处理（实际只是返回固定标签）
                    print(f"  [模拟推理服务] 收到 {len(img_data)} 字节图像数据")

                    # 返回标签
                    conn.sendall((self.response_label + "\n").encode())
            except Exception as e:
                print(f"  [模拟推理服务] 客户端处理错误: {e}")
            finally:
                conn.close()

        def server_loop():
            while self.running:
                try:
                    self.server.settimeout(1.0)
                    conn, addr = self.server.accept()
                    client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"  [模拟推理服务] 服务器错误: {e}")

        self.thread = threading.Thread(target=server_loop)
        self.thread.daemon = True
        self.thread.start()
        print(f"[✓] 模拟推理服务启动: {self.socket_path}")

    def stop(self):
        """停止模拟推理服务"""
        self.running = False
        if self.server:
            self.server.close()
        if self.thread:
            self.thread.join(timeout=2)
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        print("[✓] 模拟推理服务已停止")


def test_capture_source_mock():
    """测试抓取视频源（模拟模式）"""
    print("\n" + "="*50)
    print("测试 1: 抓取视频源 (模拟模式)")
    print("="*50)

    from obs_manager import OBSManager

    # 创建测试图像
    test_img = create_test_image(640, 480, (255, 0, 0))  # 红色图像
    mock_response = create_mock_obs_response(test_img)

    # Mock OBS WebSocket 客户端
    mock_client = Mock()
    mock_client.get_version.return_value = Mock(
        obs_version="29.0.0",
        obs_web_socket_version="5.0.0"
    )
    mock_client.get_source_screenshot.return_value = Mock(
        image_data=mock_response
    )
    mock_client.get_input_list.return_value = Mock(
        inputs=[{"inputName": "video"}, {"inputName": "camera"}]
    )

    # 创建 OBSManager 并注入 mock 客户端
    obs = OBSManager(host="localhost", port=4455)
    obs._client = mock_client

    # 测试 1: 获取视频源列表
    sources = obs.get_sources()
    print(f"[✓] 获取视频源列表: {sources}")
    assert "video" in sources, "video 应该在源列表中"

    # 测试 2: 抓取图像
    img = obs.capture_source("video", target_size=(224, 224))
    print(f"[✓] 抓取图像成功: {img.size}, 模式: {img.mode}")
    assert img.size == (224, 224), f"图像尺寸应为 (224, 224)，实际为 {img.size}"
    assert img.mode == "RGB", f"图像模式应为 RGB，实际为 {img.mode}"

    # 测试 3: 不指定尺寸
    img2 = obs.capture_source("video", target_size=None)
    print(f"[✓] 抓取原始尺寸图像: {img2.size}")

    print("\n[✓] 测试 1 通过!")
    return True


def test_capture_and_recognize_mock():
    """测试抓取并识别（模拟模式）"""
    print("\n" + "="*50)
    print("测试 2: 抓取并识别 (模拟模式)")
    print("="*50)

    from obs_manager import OBSManager

    # 启动模拟推理服务
    mock_server = MockInferenceServer(
        socket_path="/tmp/test_iidx_infer.sock",
        response_label="play"
    )
    mock_server.start()
    time.sleep(0.5)

    try:
        # 创建测试图像和 mock OBS 响应
        test_img = create_test_image(640, 480, (0, 255, 0))  # 绿色图像
        mock_response = create_mock_obs_response(test_img)

        # Mock OBS WebSocket 客户端
        mock_client = Mock()
        mock_client.get_version.return_value = Mock(
            obs_version="29.0.0",
            obs_web_socket_version="5.0.0"
        )
        mock_client.get_source_screenshot.return_value = Mock(
            image_data=mock_response
        )

        # 创建 OBSManager
        obs = OBSManager(host="localhost", port=4455)
        obs._client = mock_client

        # 测试: 抓取并识别
        result = obs.capture_and_recognize(
            source_name="video",
            infer_addr="/tmp/test_iidx_infer.sock",
            target_size=(224, 224)
        )
        print(f"[✓] 识别结果: {result}")
        assert result == "play", f"识别结果应为 'play'，实际为 '{result}'"

        print("\n[✓] 测试 2 通过!")
        return True

    finally:
        mock_server.stop()


def test_save_to_file():
    """测试保存图像到文件"""
    print("\n" + "="*50)
    print("测试 3: 保存图像到文件")
    print("="*50)

    from obs_manager import OBSManager

    # 创建测试图像和 mock OBS 响应
    test_img = create_test_image(640, 480, (0, 0, 255))  # 蓝色图像
    mock_response = create_mock_obs_response(test_img)

    # Mock OBS WebSocket 客户端
    mock_client = Mock()
    mock_client.get_version.return_value = Mock(
        obs_version="29.0.0",
        obs_web_socket_version="5.0.0"
    )
    mock_client.get_source_screenshot.return_value = Mock(
        image_data=mock_response
    )

    # 创建 OBSManager
    obs = OBSManager(host="localhost", port=4455)
    obs._client = mock_client

    # 测试: 保存到文件
    output_path = "/tmp/test_obs_capture.png"
    result_path = obs.capture_to_file("video", output_path, target_size=(224, 224))
    print(f"[✓] 图像已保存: {result_path}")

    # 验证文件
    assert os.path.exists(output_path), f"文件应该存在: {output_path}"
    saved_img = Image.open(output_path)
    print(f"[✓] 保存的图像尺寸: {saved_img.size}")
    assert saved_img.size == (224, 224), f"保存的图像尺寸应为 (224, 224)"

    # 清理
    os.remove(output_path)

    print("\n[✓] 测试 3 通过!")
    return True


def test_error_handling():
    """测试错误处理"""
    print("\n" + "="*50)
    print("测试 4: 错误处理")
    print("="*50)

    from obs_manager import OBSManager

    # 测试 1: 未连接时调用
    obs = OBSManager(host="localhost", port=4455)
    try:
        obs.get_sources()
        assert False, "应该抛出 RuntimeError"
    except RuntimeError as e:
        print(f"[✓] 未连接时正确抛出异常: {e}")

    # 测试 2: 连接检查
    assert not obs.is_connected(), "未连接时 is_connected() 应返回 False"
    print("[✓] 连接状态检查正确")

    print("\n[✓] 测试 4 通过!")
    return True


def test_real_obs(password: str = "1145141919", infer_tcp: int = None):
    """实际测试（需要 OBS 和推理服务运行）"""
    print("\n" + "="*50)
    print("实际测试: 连接真实 OBS")
    print("="*50)

    from obs_manager import OBSManager

    try:
        with OBSManager(host="localhost", port=4455, password=password) as obs:
            # 获取视频源列表
            sources = obs.get_sources()
            print(f"[✓] 可用视频源: {sources}")

            if "video" not in sources:
                print(f"[!] 警告: 'video' 不在源列表中，将使用第一个源: {sources[0] if sources else 'None'}")
                source_name = sources[0] if sources else None
            else:
                source_name = "video"

            if source_name:
                # 确定推理服务地址
                if infer_tcp:
                    infer_addr = ("127.0.0.1", infer_tcp)
                else:
                    infer_addr = "/tmp/iidx_infer.sock"

                # 抓取并识别
                print(f"\n[*] 从 '{source_name}' 抓取图像并识别...")
                result = obs.capture_and_recognize(
                    source_name=source_name,
                    infer_addr=infer_addr,
                    target_size=(224, 224)
                )
                print(f"[✓] 识别结果: {result}")

                # 同时保存截图
                output_path = "/tmp/obs_test_capture.jpg"
                obs.capture_to_file(source_name, output_path, target_size=(224, 224))
                print(f"[✓] 截图已保存: {output_path}")

        print("\n[✓] 实际测试通过!")
        return True

    except ConnectionError as e:
        print(f"[✗] 连接 OBS 失败: {e}")
        print("[*] 提示: 请确保 OBS 正在运行且 WebSocket 服务已启用")
        return False
    except Exception as e:
        print(f"[✗] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_machine_state_integration():
    """测试多机器状态机集成：两台机器独立跟踪，进入 SCORE 时自动获取分数"""
    print("\n" + "="*50)
    print("测试 5: 多机器状态机集成")
    print("="*50)

    from obs_manager import OBSManager
    from iidx_state_machine.state_machine import IIDXStateMachineManager

    # Mock OBS 客户端
    test_img = create_test_image(640, 480, (255, 0, 0))
    mock_response = create_mock_obs_response(test_img)

    mock_client = Mock()
    mock_client.get_version.return_value = Mock(
        obs_version="29.0.0",
        obs_web_socket_version="5.0.0"
    )
    mock_client.get_source_screenshot.return_value = Mock(
        image_data=mock_response
    )
    mock_client.get_input_list.return_value = Mock(
        inputs=[{"inputName": "video1"}, {"inputName": "video2"}]
    )

    obs = OBSManager(host="localhost", port=4455)
    obs._client = mock_client

    # 初始化状态机（使用同级目录中的配置）
    sm_config = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "iidx_state_machine",
        "state_machine.yaml"
    )
    obs.init_state_machine(sm_config, log_level="ERROR")

    # 注册两台机器
    obs.register_machine("cab1", source_name="video1")
    obs.register_machine("cab2", source_name="video2")

    # 为每台机器准备标签序列
    cab1_labels = ["entry", "modesel", "songsel", "play1", "score"]
    cab2_labels = ["entry", "modesel"]
    call_count = {"cab1": 0, "cab2": 0}

    def mock_capture_and_recognize(source_name, infer_addr=None, target_size=(224, 224), image_format="jpeg"):
        if source_name == "video1":
            idx = call_count["cab1"]
            call_count["cab1"] += 1
            return cab1_labels[idx]
        else:
            idx = call_count["cab2"]
            call_count["cab2"] += 1
            return cab2_labels[idx]

    def mock_capture_and_recognize_score(source_name, infer_addr=("127.0.0.1", 9877), target_size=(1920, 1080), rois=None):
        return {"1pscore": "1234", "2pscore": "5678"}

    with patch.object(obs, "capture_and_recognize", side_effect=mock_capture_and_recognize):
        with patch.object(obs, "capture_and_recognize_score", side_effect=mock_capture_and_recognize_score):
            # cab1: 前 4 帧不会触发分数
            for i in range(4):
                r = obs.process_frame("cab1")
                assert r["machine_id"] == "cab1"
                assert r["scores"] is None, f"第 {i+1} 帧不应触发分数"
                print(f"  cab1 frame {i+1}: {r['label']} -> {r['state']['current_state']}")

            # cab1 第 5 帧：score -> 触发 get_score -> 获取分数
            r = obs.process_frame("cab1")
            assert r["state"]["current_state"] == "S_SCORE"
            assert "get_score" in r["state"].get("actions_triggered", [])
            assert r["scores"] is not None
            assert r["scores"]["1pscore"] == "1234"
            print(f"  cab1 frame 5: {r['label']} -> {r['state']['current_state']} (scores={r['scores']})")

            # cab2: entry -> ENTRY
            r1 = obs.process_frame("cab2")
            assert r1["state"]["current_state"] == "ENTRY"
            print(f"  cab2 frame 1: {r1['label']} -> {r1['state']['current_state']}")

            # cab2: modesel -> MODESEL
            r2 = obs.process_frame("cab2")
            assert r2["state"]["current_state"] == "MODESEL"
            print(f"  cab2 frame 2: {r2['label']} -> {r2['state']['current_state']}")

            # 验证 cab1 仍在 S_SCORE，不受 cab2 影响
            assert obs._state_manager.get_machine_state("cab1")["current_state"] == "S_SCORE"
            assert obs._state_manager.get_machine_state("cab2")["current_state"] == "MODESEL"

    print("\n[✓] 测试 5 通过!")
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description="测试 obs_manager 模块")
    parser.add_argument("--real", action="store_true", help="运行实际测试（需要 OBS 和推理服务）")
    parser.add_argument("--password", default="1145141919", help="OBS WebSocket 密码")
    parser.add_argument("--infer-tcp", type=int, default=None, help="推理服务 TCP 端口")
    parser.add_argument("--test", choices=["1", "2", "3", "4", "5", "all"], default="all",
                        help="运行指定测试 (1=抓取源, 2=抓取识别, 3=保存文件, 4=错误处理, 5=多机器状态机集成)")

    args = parser.parse_args()

    print("="*50)
    print("obs_manager 测试开始")
    print("="*50)

    if args.real:
        success = test_real_obs(args.password, args.infer_tcp)
        sys.exit(0 if success else 1)

    # 运行模拟测试
    all_tests = [
        ("1", test_capture_source_mock, "抓取视频源"),
        ("2", test_capture_and_recognize_mock, "抓取并识别"),
        ("3", test_save_to_file, "保存到文件"),
        ("4", test_error_handling, "错误处理"),
        ("5", test_multi_machine_state_integration, "多机器状态机集成"),
    ]

    results = []
    for test_id, test_func, test_name in all_tests:
        if args.test in ("all", test_id):
            try:
                success = test_func()
                results.append((test_name, success))
            except Exception as e:
                print(f"\n[✗] 测试 {test_id} 失败: {e}")
                import traceback
                traceback.print_exc()
                results.append((test_name, False))

    # 总结
    print("\n" + "="*50)
    print("测试结果总结")
    print("="*50)
    passed = sum(1 for _, success in results if success)
    total = len(results)
    for test_name, success in results:
        status = "[✓] 通过" if success else "[✗] 失败"
        print(f"{status}: {test_name}")
    print(f"\n总计: {passed}/{total} 通过")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()

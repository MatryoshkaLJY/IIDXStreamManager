#!/usr/bin/env python3
"""
IIDX Game State Monitor - Web 工具

功能：
1. 配置 OBS 连接参数、视频源、推理服务地址
2. 每秒截取快照进行状态识别
3. 状态机跟踪游戏流程
4. 进入 SCORE 状态时自动识别分数

依赖:
    pip install flask obsws-python pillow

用法:
    python3 web_monitor.py
    # 浏览器访问 http://localhost:5001
"""

import os
import sys
import json
import time
import threading
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS

# 添加父目录到路径以导入 obs_manager
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))

try:
    from obs_manager.obs_manager import OBSManager, MachineConfig
except ImportError as e:
    print(f"无法导入 obs_manager: {e}")
    OBSManager = None
    MachineConfig = None


# ============== 数据模型 ==============

@dataclass
class MonitorConfig:
    """监控配置"""
    # OBS 连接
    obs_host: str = "localhost"
    obs_port: int = 4455
    obs_password: str = ""

    # 状态识别服务
    state_infer_host: str = "127.0.0.1"
    state_infer_port: int = 9876
    state_infer_socket: str = ""  # 如果设置，优先使用 Unix socket

    # 分数识别服务
    score_infer_host: str = "127.0.0.1"
    score_infer_port: int = 9877

    # 状态机配置
    state_machine_config: str = ""

    # 监控参数
    interval: float = 1.0  # 秒
    max_log_entries: int = 1000


@dataclass
class MachineStatus:
    """单台机器状态"""
    machine_id: str
    source_name: str
    current_state: str = "未连接"
    last_label: str = ""
    last_scores: Optional[Dict[str, str]] = None
    last_update: Optional[str] = None
    frame_count: int = 0
    score_count: int = 0
    is_active: bool = False
    error_message: str = ""


# ============== 全局状态 ==============

app = Flask(__name__, template_folder=os.path.join(BASE, "templates"))
CORS(app)

# 配置存储
_config = MonitorConfig()
_machines: Dict[str, MachineConfig] = {}
_machine_statuses: Dict[str, MachineStatus] = {}

# OBS 管理器
_obs_manager: Optional[OBSManager] = None
_monitor_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()

# 日志存储
_logs: List[Dict[str, Any]] = []
_log_lock = threading.Lock()

# 历史分数记录
_score_history: List[Dict[str, Any]] = []
_score_history_lock = threading.Lock()


# ============== 监控逻辑 ==============

def add_log(level: str, message: str, data: Optional[Dict] = None):
    """添加日志条目"""
    global _logs
    entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
        "data": data or {}
    }
    with _log_lock:
        _logs.append(entry)
        # 限制日志数量
        if len(_logs) > _config.max_log_entries:
            _logs = _logs[-_config.max_log_entries:]


def add_score_record(machine_id: str, scores: Dict[str, str], state_info: Dict):
    """添加分数记录"""
    global _score_history
    record = {
        "timestamp": datetime.now().isoformat(),
        "machine_id": machine_id,
        "scores": scores,
        "state": state_info.get("current_state", ""),
        "variables": state_info.get("variables_after", {})
    }
    with _score_history_lock:
        _score_history.append(record)
        # 只保留最近 100 条
        if len(_score_history) > 100:
            _score_history = _score_history[-100:]


def monitor_loop():
    """监控主循环"""
    global _obs_manager, _machine_statuses

    add_log("info", "监控线程启动")

    try:
        # 创建 OBSManager 实例
        _obs_manager = OBSManager(
            host=_config.obs_host,
            port=_config.obs_port,
            password=_config.obs_password or None
        )

        # 连接 OBS
        add_log("info", f"正在连接 OBS {_config.obs_host}:{_config.obs_port}...")
        _obs_manager.connect()
        add_log("success", "已连接到 OBS")

        # 初始化状态机
        if _config.state_machine_config and os.path.exists(_config.state_machine_config):
            add_log("info", f"加载状态机配置: {_config.state_machine_config}")
            _obs_manager.init_state_machine(_config.state_machine_config, log_level="WARNING")
        else:
            add_log("warning", "未配置状态机配置文件")
            return

        # 确定推理地址
        if _config.state_infer_socket:
            state_infer_addr = _config.state_infer_socket
        else:
            state_infer_addr = (_config.state_infer_host, _config.state_infer_port)

        score_infer_addr = (_config.score_infer_host, _config.score_infer_port)

        # 注册机器
        for machine_id, machine_cfg in _machines.items():
            _obs_manager.register_machine(
                machine_id=machine_id,
                source_name=machine_cfg.source_name,
                state_infer_addr=state_infer_addr,
                score_infer_addr=score_infer_addr
            )
            # 初始化状态
            if machine_id not in _machine_statuses:
                _machine_statuses[machine_id] = MachineStatus(
                    machine_id=machine_id,
                    source_name=machine_cfg.source_name
                )
            _machine_statuses[machine_id].is_active = True
            add_log("info", f"注册机器: {machine_id} (源: {machine_cfg.source_name})")

        # 主循环
        add_log("info", f"开始监控循环，间隔 {_config.interval}s")

        while not _stop_event.is_set():
            for machine_id in _machines:
                if _stop_event.is_set():
                    break

                try:
                    # 处理单帧
                    result = _obs_manager.process_frame(machine_id)

                    # 更新状态
                    status = _machine_statuses.get(machine_id)
                    if status:
                        status.frame_count += 1
                        status.last_label = result.get("label", "")
                        status.last_update = datetime.now().isoformat()

                        state_result = result.get("state", {})
                        if state_result:
                            status.current_state = state_result.get("current_state", "未知")

                        # 检查是否触发分数识别
                        scores = result.get("scores")
                        if scores:
                            status.last_scores = scores
                            status.score_count += 1
                            add_score_record(machine_id, scores, state_result)
                            add_log(
                                "score",
                                f"[{machine_id}] 识别到分数",
                                {"scores": scores, "state": state_result}
                            )

                        # 记录状态转换
                        if state_result and state_result.get("transition"):
                            add_log(
                                "state",
                                f"[{machine_id}] 状态转换: {state_result.get('old_state')} -> {state_result.get('current_state')}",
                                state_result
                            )

                except Exception as e:
                    error_msg = str(e)
                    if machine_id in _machine_statuses:
                        _machine_statuses[machine_id].error_message = error_msg
                    add_log("error", f"[{machine_id}] 处理帧失败: {error_msg}")

            # 等待下一次轮询
            _stop_event.wait(_config.interval)

    except Exception as e:
        add_log("error", f"监控线程异常: {str(e)}")

    finally:
        # 清理
        if _obs_manager:
            try:
                _obs_manager.disconnect()
            except:
                pass

        # 更新所有机器状态为离线
        for status in _machine_statuses.values():
            status.is_active = False

        add_log("info", "监控线程已停止")


# ============== API 路由 ==============

@app.route("/")
def index():
    """主页"""
    return render_template("monitor.html")


@app.route("/api/config", methods=["GET"])
def get_config():
    """获取当前配置"""
    return jsonify(asdict(_config))


@app.route("/api/config", methods=["POST"])
def update_config():
    """更新配置"""
    global _config

    data = request.get_json() or {}

    # 更新配置
    for key, value in data.items():
        if hasattr(_config, key):
            setattr(_config, key, value)

    return jsonify({"ok": True, "config": asdict(_config)})


@app.route("/api/machines", methods=["GET"])
def get_machines():
    """获取所有机器配置"""
    result = []
    for machine_id, cfg in _machines.items():
        result.append({
            "machine_id": machine_id,
            "source_name": cfg.source_name
        })
    return jsonify(result)


@app.route("/api/machines", methods=["POST"])
def add_machine():
    """添加机器"""
    global _machines

    data = request.get_json() or {}
    machine_id = data.get("machine_id", "").strip()
    source_name = data.get("source_name", "").strip()

    if not machine_id or not source_name:
        return jsonify({"error": "machine_id 和 source_name 不能为空"}), 400

    if machine_id in _machines:
        return jsonify({"error": f"机器 {machine_id} 已存在"}), 400

    _machines[machine_id] = MachineConfig(
        machine_id=machine_id,
        source_name=source_name
    )

    # 初始化状态
    _machine_statuses[machine_id] = MachineStatus(
        machine_id=machine_id,
        source_name=source_name
    )

    add_log("info", f"添加机器: {machine_id}")
    return jsonify({"ok": True})


@app.route("/api/machines/<machine_id>", methods=["DELETE"])
def remove_machine(machine_id: str):
    """删除机器"""
    global _machines

    if machine_id not in _machines:
        return jsonify({"error": "机器不存在"}), 404

    del _machines[machine_id]
    if machine_id in _machine_statuses:
        del _machine_statuses[machine_id]

    add_log("info", f"删除机器: {machine_id}")
    return jsonify({"ok": True})


@app.route("/api/status", methods=["GET"])
def get_status():
    """获取所有机器状态"""
    result = {}
    for machine_id, status in _machine_statuses.items():
        result[machine_id] = asdict(status)
    return jsonify(result)


@app.route("/api/monitor/start", methods=["POST"])
def start_monitor():
    """启动监控"""
    global _monitor_thread, _stop_event

    if _monitor_thread and _monitor_thread.is_alive():
        return jsonify({"error": "监控已在运行中"}), 400

    if not _machines:
        return jsonify({"error": "请先添加至少一台机器"}), 400

    if not _config.state_machine_config:
        return jsonify({"error": "请配置状态机配置文件路径"}), 400

    if not os.path.exists(_config.state_machine_config):
        return jsonify({"error": f"状态机配置文件不存在: {_config.state_machine_config}"}), 400

    # 重置停止事件
    _stop_event.clear()

    # 启动监控线程
    _monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    _monitor_thread.start()

    return jsonify({"ok": True})


@app.route("/api/monitor/stop", methods=["POST"])
def stop_monitor():
    """停止监控"""
    global _stop_event

    if not _monitor_thread or not _monitor_thread.is_alive():
        return jsonify({"error": "监控未在运行"}), 400

    _stop_event.set()
    _monitor_thread.join(timeout=5)

    return jsonify({"ok": True})


@app.route("/api/monitor/status", methods=["GET"])
def get_monitor_status():
    """获取监控运行状态"""
    is_running = _monitor_thread is not None and _monitor_thread.is_alive()
    return jsonify({
        "is_running": is_running,
        "machine_count": len(_machines)
    })


@app.route("/api/logs", methods=["GET"])
def get_logs():
    """获取日志"""
    level = request.args.get("level", "")
    limit = request.args.get("limit", 100, type=int)

    with _log_lock:
        logs = _logs[:]

    # 过滤
    if level:
        logs = [log for log in logs if log["level"] == level]

    # 限制数量
    logs = logs[-limit:]

    return jsonify(logs)


@app.route("/api/logs/clear", methods=["POST"])
def clear_logs():
    """清空日志"""
    global _logs
    with _log_lock:
        _logs = []
    return jsonify({"ok": True})


@app.route("/api/scores", methods=["GET"])
def get_scores():
    """获取分数历史"""
    global _score_history
    limit = request.args.get("limit", 50, type=int)
    machine_id = request.args.get("machine_id", "")

    with _score_history_lock:
        scores = _score_history[:]

    # 过滤
    if machine_id:
        scores = [s for s in scores if s["machine_id"] == machine_id]

    # 限制数量
    scores = scores[-limit:]

    return jsonify(scores)


@app.route("/api/obs/sources", methods=["GET"])
def get_obs_sources():
    """获取 OBS 视频源列表（需要已连接）"""
    if not _obs_manager or not _obs_manager.is_connected():
        return jsonify({"error": "OBS 未连接"}), 400

    try:
        sources = _obs_manager.get_sources()
        return jsonify(sources)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/test/obs", methods=["POST"])
def test_obs_connection():
    """测试 OBS 连接"""
    data = request.get_json() or {}

    host = data.get("host", _config.obs_host)
    port = data.get("port", _config.obs_port)
    password = data.get("password", _config.obs_password)

    try:
        test_obs = OBSManager(
            host=host,
            port=port,
            password=password or None
        )
        test_obs.connect()
        sources = test_obs.get_sources()
        test_obs.disconnect()

        return jsonify({
            "ok": True,
            "message": f"连接成功，发现 {len(sources)} 个视频源",
            "sources": sources
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"连接失败: {str(e)}"
        }), 400


@app.route("/api/save_config", methods=["POST"])
def save_config_to_file():
    """保存配置到文件"""
    config_path = os.path.join(BASE, "monitor_config.json")

    data = {
        "config": asdict(_config),
        "machines": {
            mid: {"machine_id": m.machine_id, "source_name": m.source_name}
            for mid, m in _machines.items()
        }
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    add_log("info", f"配置已保存到: {config_path}")
    return jsonify({"ok": True, "path": config_path})


@app.route("/api/load_config", methods=["POST"])
def load_config_from_file():
    """从文件加载配置"""
    global _config, _machines

    config_path = os.path.join(BASE, "monitor_config.json")

    if not os.path.exists(config_path):
        return jsonify({"error": "配置文件不存在"}), 404

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 加载配置
        config_data = data.get("config", {})
        for key, value in config_data.items():
            if hasattr(_config, key):
                setattr(_config, key, value)

        # 加载机器
        machines_data = data.get("machines", {})
        _machines.clear()
        for mid, mdata in machines_data.items():
            _machines[mid] = MachineConfig(
                machine_id=mdata["machine_id"],
                source_name=mdata["source_name"]
            )
            _machine_statuses[mid] = MachineStatus(
                machine_id=mid,
                source_name=mdata["source_name"]
            )

        add_log("info", f"配置已从 {config_path} 加载")
        return jsonify({"ok": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def load_config_on_startup():
    """启动时自动加载配置"""
    global _config, _machines

    # 尝试自动检测状态机配置文件
    auto_detect_state_machine()

    config_path = os.path.join(BASE, "monitor_config.json")

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 加载配置
            config_data = data.get("config", {})
            for key, value in config_data.items():
                if hasattr(_config, key):
                    # 如果自动检测到了状态机配置，但配置文件中没有，使用自动检测的
                    if key == "state_machine_config" and not value and _config.state_machine_config:
                        continue
                    setattr(_config, key, value)

            # 加载机器
            machines_data = data.get("machines", {})
            for mid, mdata in machines_data.items():
                _machines[mid] = MachineConfig(
                    machine_id=mdata["machine_id"],
                    source_name=mdata["source_name"]
                )
                _machine_statuses[mid] = MachineStatus(
                    machine_id=mid,
                    source_name=mdata["source_name"]
                )

            print(f"[启动] 已加载配置: {config_path}")
        except Exception as e:
            print(f"[启动] 加载配置失败: {e}")


def auto_detect_state_machine():
    """自动检测状态机配置文件路径"""
    global _config

    # 可能的配置文件位置
    possible_paths = [
        os.path.join(os.path.dirname(BASE), "iidx_state_machine", "state_machine.yaml"),
        os.path.join(BASE, "..", "iidx_state_machine", "state_machine.yaml"),
        os.path.join(BASE, "state_machine.yaml"),
    ]

    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            _config.state_machine_config = abs_path
            print(f"[启动] 自动检测到状态机配置: {abs_path}")
            return

    print("[启动] 未找到状态机配置文件，请手动配置")


# ============== 主入口 ==============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="IIDX Game State Monitor - Web 工具")
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址")
    parser.add_argument("--port", type=int, default=5001, help="端口")
    parser.add_argument("--debug", action="store_true", help="调试模式")

    args = parser.parse_args()

    # 启动时加载配置
    load_config_on_startup()

    print(f"=" * 50)
    print(f"IIDX Game State Monitor")
    print(f"=" * 50)
    print(f"访问地址: http://localhost:{args.port}")
    print(f"=" * 50)

    app.run(host=args.host, port=args.port, debug=args.debug)

# IIDX Game State Monitor

基于 Web 的 IIDX 游戏状态监控工具，支持多机台实时监控、状态识别和自动分数捕获。

## 功能特性

- **OBS 集成**: 连接 OBS WebSocket，实时抓取视频源
- **状态识别**: 每秒截取快照，通过推理服务识别游戏状态
- **状态机跟踪**: 基于 YAML 配置的状态机管理游戏流程
- **自动分数捕获**: 进入 SCORE 状态时自动识别分数
- **多机台支持**: 同时监控多台游戏机
- **Web 界面**: 现代化的实时监控面板

## 快速开始

### 1. 安装依赖

```bash
pip install flask flask-cors obsws-python pillow pyyaml
```

### 2. 启动服务

```bash
# 使用启动脚本
chmod +x start_monitor.sh
./start_monitor.sh

# 或直接启动
python3 web_monitor.py
```

### 3. 访问界面

打开浏览器访问: http://localhost:5001

## 使用步骤

### 1. 配置 OBS 连接

- 在 **OBS 连接配置** 面板中填写:
  - 主机地址 (默认: localhost)
  - 端口 (默认: 4455)
  - 密码 (如果 WebSocket 设置了密码)
- 点击 **测试连接** 验证配置

### 2. 配置推理服务

- **状态识别服务**: 配置状态识别服务的地址 (默认 TCP 9876 或 Unix Socket)
- **分数识别服务**: 配置分数识别服务的地址 (默认 TCP 9877)

### 3. 配置状态机

- 指定状态机 YAML 配置文件路径
- 示例配置见 `iidx_state_machine/state_machine.yaml`

### 4. 添加机器

- 在 **机器管理** 面板中添加机台:
  - 机器 ID: 唯一标识 (如 `cab1`, `cab2`)
  - 视频源名称: OBS 中的视频源名称 (如 `video`, `kkm`)

### 5. 启动监控

- 点击 **启动监控** 按钮开始监控
- 实时查看状态、日志和分数记录

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config` | 获取配置 |
| POST | `/api/config` | 更新配置 |
| GET | `/api/machines` | 获取机器列表 |
| POST | `/api/machines` | 添加机器 |
| DELETE | `/api/machines/<id>` | 删除机器 |
| GET | `/api/status` | 获取所有机器状态 |
| POST | `/api/monitor/start` | 启动监控 |
| POST | `/api/monitor/stop` | 停止监控 |
| GET | `/api/monitor/status` | 获取监控运行状态 |
| GET | `/api/logs` | 获取日志 |
| POST | `/api/logs/clear` | 清空日志 |
| GET | `/api/scores` | 获取分数历史 |
| POST | `/api/test/obs` | 测试 OBS 连接 |
| POST | `/api/save_config` | 保存配置到文件 |
| POST | `/api/load_config` | 从文件加载配置 |

## 配置存储

配置会自动保存到 `monitor_config.json` 文件，包含:
- OBS 连接配置
- 推理服务地址
- 机器列表

## 依赖项目

本项目需要以下服务运行:

1. **OBS Studio** + **obs-websocket** 插件
2. **状态识别服务** (`iidx_state_reco/serve.py`)
3. **分数识别服务** (`iidx_score_reco/serve.py`)

启动顺序:
```bash
# 1. 启动 OBS Studio

# 2. 启动状态识别服务
python3 ../iidx_state_reco/serve.py --model classifier.onnx --tcp 9876

# 3. 启动分数识别服务
python3 ../iidx_score_reco/serve.py

# 4. 启动监控 Web 服务
python3 web_monitor.py
```

## 界面截图

界面包含以下面板:
- **OBS 连接配置**: 配置 OBS WebSocket 连接
- **推理服务配置**: 配置状态识别和分数识别服务
- **状态机配置**: 配置状态机 YAML 文件路径
- **机器管理**: 添加/删除监控机台
- **实时状态**: 显示各机台的当前状态、帧数、分数等
- **运行日志**: 实时显示状态转换和错误信息
- **分数记录**: 记录所有识别到的分数历史

## 注意事项

1. 确保 OBS WebSocket 插件已安装并启用
2. 确保推理服务在监控启动前已经运行
3. 状态机配置文件路径必须是绝对路径或相对于 `web_monitor.py` 的相对路径
4. 配置文件会自动保存，下次启动时自动加载

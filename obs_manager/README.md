# OBS Manager

与 OBS Studio 交互的 Python 工具模块，支持抓取视频源图像、调用外部推理服务进行游戏画面状态识别与分数识别，并可选集成 `iidx_state_machine` 实现多台游戏机的状态跟踪。

## 功能

- **连接 OBS WebSocket**：通过 `obws-python` 连接 OBS Studio。
- **抓取视频源截图**：获取指定输入源的图像并调整尺寸。
- **状态识别**：将截图发送到 `iidx_state_reco` 推理服务，获取游戏画面分类标签（如 `entry`、`play1`、`score` 等）。
- **分数识别**：将高分区域截图发送到 `iidx_score_reco` 推理服务，识别 ROI 中的数字分数。
- **多机器状态跟踪**：集成 `iidx_state_machine`，支持注册多台游戏机，分别维护独立的游戏状态机，并在进入分数状态时自动触发分数识别。

## 安装依赖

```bash
pip install obsws-python pillow
```

> 若使用 Python 3.9 以下版本，请同时安装 `pyyaml`。

## 快速开始

### 1. 基本用法：抓取并识别单张图像

```python
from obs_manager import OBSManager

with OBSManager(host="localhost", port=4455, password="your_password") as obs:
    label = obs.capture_and_recognize(
        source_name="video",
        infer_addr=("127.0.0.1", 9876)
    )
    print(f"状态识别结果: {label}")
```

### 2. 高分区域识别

```python
from obs_manager import OBSManager

with OBSManager(host="localhost", port=4455, password="your_password") as obs:
    scores = obs.capture_and_recognize_score(
        source_name="video",
        infer_addr=("127.0.0.1", 9877)
    )
    print(f"分数: {scores}")
```

### 3. 多机器状态跟踪（推荐）

```python
from obs_manager import OBSManager

obs = OBSManager(host="localhost", port=4455, password="your_password")
obs.connect()

# 初始化状态机（指向 iidx_state_machine 的配置文件）
obs.init_state_machine("../iidx_state_machine/state_machine.yaml")

# 注册两台游戏机，每个对应不同的 OBS 视频源
obs.register_machine("cab1", source_name="video1")
obs.register_machine("cab2", source_name="video2")

# 开始轮询，每秒处理一帧
obs.run(interval=1.0)
```

> `run()` 会自动循环：
> 1. 抓取图像 → 2. 状态识别 → 3. 输入状态机 → 4. 若触发 `get_score` 则自动调用分数识别。

也可以手动单帧处理：

```python
result = obs.process_frame("cab1")
print(result)
```

返回示例：

```json
{
  "machine_id": "cab1",
  "timestamp": "2026-03-31T12:00:00.000000",
  "label": "score",
  "state": {
    "old_state": "S_PLAY",
    "current_state": "S_SCORE",
    "actions_triggered": ["exit_play_mode", "get_score"],
    "handled": true,
    ...
  },
  "scores": {
    "1pscore": "2356",
    "2pscore": "1987"
  }
}
```

## 命令行用法

```bash
python obs_manager.py \
  --host localhost \
  --port 4455 \
  --password your_password \
  --source video \
  --infer-tcp 9876
```

### CLI 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--host` | OBS WebSocket 主机 | `localhost` |
| `--port` | OBS WebSocket 端口 | `4455` |
| `--password` | OBS WebSocket 密码 | `None` |
| `--source` | 视频源名称 | `video` |
| `--infer-tcp` | 状态识别服务 TCP 端口 | `9876` |
| `--infer-sock` | 状态识别服务 Unix socket 路径（传入后优先于 TCP） | `None` |
| `--size` | 目标尺寸 `宽 高` | `224 224` |
| `--output, -o` | 同时保存截图到文件 | `None` |

## API 参考

### `OBSManager`

#### 连接管理
- `connect()` — 连接 OBS WebSocket
- `disconnect()` — 断开连接
- `is_connected()` — 检查连接状态

#### 图像抓取与识别
- `capture_source(source_name, target_size, image_format)` → `PIL.Image`
- `capture_and_recognize(source_name, infer_addr, target_size, image_format)` → `str`
- `capture_and_recognize_score(source_name, infer_addr, target_size, rois)` → `dict`
- `capture_to_file(source_name, output_path, target_size)` → `str`
- `capture_score_regions(source_name, output_dir, target_size, rois)` → `dict`

#### 状态机集成（多机器）
- `init_state_machine(config_path, log_level="INFO", simple_mode=False)` — 初始化 `IIDXStateMachineManager`
- `register_machine(machine_id, source_name, state_infer_addr, score_infer_addr)` — 注册游戏机
- `process_frame(machine_id)` → `dict` — 处理单帧（含状态机推进与条件分数识别）
- `run(interval=1.0)` — 轮询所有注册机器

### `MachineConfig`

每台游戏机的配置数据结构：

```python
@dataclass
class MachineConfig:
    machine_id: str
    source_name: str
    state_infer_addr: Union[str, Tuple[str, int]] = ("127.0.0.1", 9876)
    score_infer_addr: Tuple[str, int] = ("127.0.0.1", 9877)
```

## 测试

```bash
# 运行全部模拟测试
python test_obs_manager.py

# 运行指定测试
python test_obs_manager.py --test 5
```

## 架构与数据流

```
OBS Studio
    |
    | WebSocket
    v
OBSManager
    |
    |-- capture_and_recognize() -> TCP/UnixSocket -> iidx_state_reco
    |                               返回画面标签 (entry/play1/score...)
    |
    |-- capture_and_recognize_score() -> TCP -> iidx_score_reco
    |                                    返回 JSON 分数
    |
    v
IIDXStateMachineManager (iidx_state_machine)
    |
    +-- machine_id="cab1" -> IIDXStateMachine
    +-- machine_id="cab2" -> IIDXStateMachine
```

## 注意事项

- **Windows 兼容**：默认使用 TCP 地址 `("127.0.0.1", 9876)` 连接推理服务；若需要使用 Unix socket，请在 Linux/macOS 环境下显式传入 `--infer-sock`。
- **状态机配置文件路径**：`init_state_machine()` 会自动尝试从同级目录 `../iidx_state_machine/state_machine.py` 导入 `IIDXStateMachineManager`，无需手动修改 `PYTHONPATH`。
- **自动分数识别**：仅当状态机的 `actions_triggered` 中包含 `get_score` 时（即进入任一 `SCORE` 状态），`process_frame()` 才会调用分数识别服务，避免不必要的请求。

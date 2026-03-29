# IIDX Stream State Machine

## 项目概述

本项目实现 IIDX (beatmania IIDX) 街机游戏的状态机，配合 `iidx_state_reco` 的识别逻辑，向 OBS 等直播软件发送指令以切换场景、触发细节识别等。

## 状态机设计

### 全局状态流转

```
机器闲置 (blank) -> interlude -> entry -> interlude -> modesel -> interlude -> 【游玩阶段】
-> interlude -> entry -> blank -> 机器闲置
```

**关键判定规则：**
- `blank` 不一定代表机器闲置（游戏加载时也可能黑屏）
- `entry` 既代表玩家刷卡上机，也代表玩家结束游戏下机
- **机器空闲判定**：一轮游戏结束后，`entry -> blank` 表示玩家下机，机器回到空闲状态

### 状态定义

#### 基础状态

| 状态 | 说明 |
|------|------|
| `IDLE` | 机器闲置，等待游戏开始 |
| `INTERLUDE` | 过渡/加载画面，黑屏或转场 |
| `ENTRY` | 玩家登入画面，显示玩家信息 |
| `MODESEL` | 模式选择画面 |
| `PAY` | 投币/支付确认画面 |
| `SONGSEL` | 选曲画面 |
| `CONFIRM` | 曲目确认画面 |
| `ACONFIRM` | Arena/BPL 对战确认画面 |
| `PLAY` | 游玩中，音符下落 |
| `DEATH` | 曲失败（血条归零） |
| `SCORE` | 成绩结算画面（单首） |

#### 模式特有状态

| 状态 | 模式 | 说明 |
|------|------|------|
| `BWAIT` | BPL Battle | BPL 对战等待画面 |
| `BRANK` | BPL Battle | BPL 对战排名结算 |
| `AWAIT` | Arena | 竞技场等待画面 |
| `ARANK` | Arena | 竞技场排名结算 |
| `DANSEL` | Dan | 段位选择画面 |
| `DANSCORE` | Dan | 段位总成绩结算 |

### 【曲目进程】子状态机

所有模式的游玩核心都是【曲目进程】，其内部流转：

```
                    ┌──────────────────┐
                    ▼                  │
┌──────┐    ┌──────┐    ┌──────┐    ┌─┴────┐
│ PLAY │───▶│DEATH │───▶│ PLAY │───▶│SCORE │
└──────┘    └──────┘    └──────┘    └──┬───┘
     │                                 │
     │         ┌───────────────────────┘
     │         ▼
     └─────▶ INTERLUDE
               │
               ▼
             PLAY (下一首)
```

**规则：**
- `DEATH` 可能出现也可能不出现
- `SCORE` 可能因玩家快速跳过而识别不到
- `DEATH` 后可接 `PLAY`（接关/下一首）
- `INTERLUDE` 后可接 `PLAY`（正常下一首）

### 各模式状态机

#### 1. BPL Battle 模式

```
BWAIT -> INTERLUDE -> SONGSEL -> INTERLUDE -> { ACONFIRM -> CONFIRM -> 【曲目进程】 } -> BRANK
```

- `{}` 内部分重复多次（多首曲目对战）

#### 2. Arena 模式

```
AWAIT -> INTERLUDE -> SONGSEL -> INTERLUDE -> { ACONFIRM -> CONFIRM -> 【曲目进程】 } -> ARANK
```

- `{}` 内部分重复多次

#### 3. Dan（段位认定）模式

```
DANSEL -> CONFIRM -> { 【曲目进程】 } -> DANSCORE
```

- `{}` 内部分重复多次（通常 4 首）
- **特殊规则：** 如果【曲目进程】中遇到 `DEATH`，立即跳出循环进入 `DANSCORE`

#### 4. 标准模式（Standard）

```
{ SONGSEL -> 【曲目进程】 }
```

- `{}` 内部分重复数次（玩家连续游玩多首）
- **特殊规则：** 支持快捷重启（Quick Retry）检测

##### 快捷重启（Quick Retry）

在 standard 模式下，玩家失败后可以快速重启同一首歌：

**快捷重启的状态流转：**
```
# 路径 1：死亡后直接重启
PLAY -> DEATH -> PLAY

# 路径 2：查看成绩后重启
PLAY -> DEATH -> SCORE -> INTERLUDE -> PLAY
```

**计数器逻辑：**
- `song_count`：已游玩曲目数（同一首歌多次尝试只计 1 次）
- `try_count`：当前曲目的尝试次数（每次快捷重启 +1）

**判定规则：**
| 转移路径 | 判定结果 | song_count | try_count |
|----------|----------|------------|-----------|
| `INTERLUDE -> PLAY` | 新曲开始 | +1 | 重置为 1 |
| `DEATH -> PLAY` | 快捷重启 | 不变 | +1 |
| `SCORE -> PLAY` | 快捷重启 | 不变 | +1 |
| `SCORE -> INTERLUDE` | 歌曲正常完成 | - | - |
| `DEATH -> INTERLUDE` | 歌曲失败结束 | - | - |

**输出示例：**
```
[STATE] play         -> death        | Mode: STANDARD     [Song 1.1]
[STATE] death        -> play         | Mode: STANDARD     [Song 1.2]  ← 第1首歌第2次尝试
[STATE] play         -> death        | Mode: STANDARD     [Song 1.2]
[STATE] death        -> score        | Mode: STANDARD     [Song 1.2]
[STATE] score        -> interlude    | Mode: STANDARD
[STATE] interlude    -> play         | Mode: STANDARD     [Song 2.1]  ← 第2首歌第1次尝试
```

### 完整状态转移表

| 当前状态 | 可能转移 | 条件/说明 |
|----------|----------|-----------|
| `IDLE` | `INTERLUDE` | 检测到游戏启动 |
| `INTERLUDE` | `ENTRY`, `SONGSEL`, `PLAY`, `MODESEL`, `PAY`, `BRANK`, `ARANK`, `DANSCORE` | 根据上下文和模式判断 |
| `ENTRY` | `INTERLUDE` | 登入完成 |
| `MODESEL` | `PAY` | 选择模式后 |
| `PAY` | `INTERLUDE` | 支付完成 |
| `BWAIT` | `INTERLUDE` | BPL 匹配完成 |
| `AWAIT` | `INTERLUDE` | Arena 匹配完成 |
| `SONGSEL` | `INTERLUDE`, `CONFIRM` | 选曲完成 |
| `ACONFIRM` | `CONFIRM` | 对战确认 |
| `CONFIRM` | `PLAY` | 曲目确认，开始游戏 |
| `PLAY` | `DEATH`, `SCORE`, `INTERLUDE` | 曲终结算或失败 |
| `DEATH` | `PLAY`, `INTERLUDE`, `DANSCORE` | 接关/下一首或结束 |
| `SCORE` | `INTERLUDE` | 成绩显示完成 |
| `BRANK` | `INTERLUDE`, `IDLE` | 对战结束 |
| `ARANK` | `INTERLUDE`, `IDLE` | 竞技结束 |
| `DANSEL` | `CONFIRM` | 段位选择完成 |
| `DANSCORE` | `INTERLUDE`, `IDLE` | 段位结算完成 |

### 防抖机制

**连续两帧相同状态才进行状态转移**

```python
# 伪代码
if current_recognized_state == last_recognized_state:
    if current_state != current_recognized_state:
        # 执行状态转移
        transition_to(current_recognized_state)
```

### 异常处理与重置

**重置条件：**
- 机器因调试等原因脱离正常逻辑
- 检测到 `ENTRY` 状态（新一轮游戏开始）

**重置操作：**
1. 清空当前模式上下文
2. 状态机回到初始状态
3. 重新开始状态流转

## OBS 场景映射

| 游戏状态 | OBS 场景 | 说明 |
|----------|----------|------|
| `BLANK` | 待机画面 | 机器闲置/黑屏，玩家可刷卡上机 |
| `IDLE` | 待机画面 | 开机画面，等待游戏启动 |
| `MODESEL` | 准备画面 | 显示投币提示 |
| `SONGSEL` | 选曲画面 | 可触发曲名识别 |
| `PLAY` | 游戏画面 | 主游玩画面 |
| `DEATH` | 失败画面 | 可选特效 |
| `SCORE` | 成绩画面 | 可触发成绩识别 |
| `BRANK`/`ARANK`/`DANSCORE` | 结算画面 | 最终成绩展示 |
| `INTERLUDE` | 过渡画面 | 黑屏或保持上一场景 |
| `ENTRY` | 准备画面 | 玩家登入/登出画面 |

**注意：** `BLANK` 在游戏过程中也可能出现（加载时），只有当 `entry -> blank` 时才表示机器真正回到空闲状态。

## 实现要点

1. **状态识别输入：** 接收 `iidx_state_reco` 的输出状态
2. **防抖缓存：** 维护最近两帧的识别结果
3. **模式上下文：** 记录当前游戏模式（BPL/Arena/Dan/Standard）
4. **快捷重启检测：** Standard 模式下检测 `DEATH->PLAY` 或 `SCORE->PLAY` 转移，使用 `try_count` 记录尝试次数
5. **场景触发：** 状态变更时通过 OBS WebSocket 发送场景切换指令
6. **细节识别触发：** 在特定状态（如 `SONGSEL`, `SCORE`）触发额外识别逻辑
7. **日志记录：** 记录完整的状态流转历史，便于调试

## 使用示例

### 基础使用

```python
from state_machine import IIDXStateMachine

sm = IIDXStateMachine()

# 模拟接收识别结果（实际从 iidx_state_reco 获取）
for frame_state in recognition_sequence:
    current_state = sm.feed(frame_state)
    print(f"Current: {current_state.value}")
```

### 自定义状态转移回调

```python
def on_transition(from_state, to_state, context):
    print(f"Transition: {from_state.value} -> {to_state.value}")
    # 发送 OBS 指令或执行其他操作

sm = IIDXStateMachine(on_transition=on_transition)
```

### 处理真实识别数据

```bash
# 先用 iidx_state_reco 识别
python3 ../iidx_state_reco/infer_onnx.py --model classifier.onnx data/kbpl/ > states.txt

# 提取状态序列
grep -oP '→ \K\w+' states.txt > kbpl_states.txt

# 用状态机处理
python3 test_with_real_data.py kbpl_states.txt
```

## 目录结构

```
iidx_stream_state_machine/
├── CLAUDE.md              # 本文件：状态机设计文档
├── pyproject.toml         # 项目配置
├── src/
│   ├── __init__.py        # 包导出
│   ├── state_machine.py   # 核心状态机实现
│   ├── config.py          # 配置管理
│   ├── demo.py            # 使用示例/演示
│   └── integration.py     # 与识别服务集成示例
└── tests/
    └── test_state_machine.py  # 单元测试
```

## 依赖

- `obs-websocket-py` 或 `simpleobsws` - OBS WebSocket 通信
- `iidx_state_reco` - 状态识别模块（同级目录）

## 后续扩展

- [ ] 支持更多 IIDX 版本的状态识别
- [ ] 自定义场景映射配置
- [ ] 状态流转数据统计
- [ ] 异常检测与告警

## 工作日志

### 2026-03-28: Standard 模式快捷重启检测

**任务**: 细化 standard 模式下的快捷重启逻辑，防止重复计数。

**已完成**:
1. 新增 `try_count` 计数器字段，记录当前曲目的尝试次数
2. 新增 `_last_song_completed` 标记，区分正常完成与快捷重启
3. 实现快捷重启检测逻辑：
   - `DEATH -> PLAY`: 判定为快捷重启，`try_count + 1`
   - `SCORE -> PLAY`: 判定为快捷重启，`try_count + 1`
   - `INTERLUDE -> PLAY`: 正常新曲，`song_count + 1`, `try_count = 1`
4. 更新状态输出格式：`[Song {song_count}.{try_count}]`
5. 更新 `get_status()` 返回结果，包含 `try_count`
6. 完善文档：添加 Standard 模式快捷重启详细说明和判定规则表

**文件变更**:
- `src/state_machine.py`: 核心逻辑实现
- `CLAUDE.md`: 文档更新

**输出示例**:
```
[STATE] play         -> death        | Mode: STANDARD     [Song 1.1]
[STATE] death        -> play         | Mode: STANDARD     [Song 1.2]
[STATE] play         -> death        | Mode: STANDARD     [Song 1.2]
[STATE] death        -> score        | Mode: STANDARD     [Song 1.2]
[STATE] score        -> interlude    | Mode: STANDARD
[STATE] interlude    -> play         | Mode: STANDARD     [Song 2.1]
```

**关键设计**:
- Standard 模式特有：其他模式（BPL/Arena/Dan）不启用快捷重启检测
- 使用防抖机制：连续两帧相同状态才触发转移，减少误判
- 向后兼容：新增字段不影响原有接口

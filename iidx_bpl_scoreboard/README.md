# BPL Scoreboard - beatmania IIDX 比赛计分板

一个基于 Web 的实时比赛计分板，支持 WebSocket 指令控制、选手名隐藏揭示效果和 1V1/2V2 模式。

![预览](./example/Screenshot%20From%202026-03-30%2021-30-21.png)

## 功能特性

- 🎮 **BPL 风格设计** - 还原原版的科幻游戏风格
- 📡 **WebSocket 指令协议** - `init` 初始化、`score` 计分
- 👻 **选手名隐藏揭示** - 分数更新前显示 `???`，更新后动画揭示
- ⚔️ **1V1 / 2V2 支持** - 自动适配单双打显示
- 🏷️ **比赛主题显示** - 每局下方显示主题（如 THEME: SCRATCH）
- 🎨 **动态颜色系统** - 背景渐变自动跟随队伍主色
- 📺 **OBS 优化** - 固定 1920x1080 分辨率

## 快速开始

### 1. 启动 WebSocket 服务器

使用 Python 版本（推荐）：

```bash
cd testbench
pip install -r requirements.txt
python server.py
```

或使用 Node.js 版本：

```bash
npm install ws
node websocket-server.js
```

服务器启动后：
- WebSocket: `ws://localhost:8080`

### 2. 打开计分板

用浏览器打开 `index.html`（或使用本地 HTTP 服务器）。

### 3. 测试指令

使用 Python testbench：

```bash
cd testbench
python testbench.py --demo
```

或在服务器控制台手动输入指令：

```
init                    # 初始化比赛
score 1 2 0             # 第1回合：左2分，右0分
score 2 4 1             # 第2回合：左4分，右1分
reset                   # 重置所有分数
exit                    # 停止服务器
```

## WebSocket 指令协议

### INIT - 初始化比赛

```json
{
  "cmd": "init",
  "data": {
    "stageName": "レギュラーステージ",
    "matchNumber": 12,
    "leftTeam": {
      "name": "SILK HAT",
      "logo": "🎩",
      "colors": {
        "primary": "#c0c0c0",
        "secondary": "#ffffff"
      }
    },
    "rightTeam": {
      "name": "GAME PANIC",
      "logo": "🎮",
      "colors": {
        "primary": "#ffd700",
        "secondary": "#000000"
      }
    },
    "matches": [
      {
        "type": "1v1",
        "leftPlayers": ["CHEPY."],
        "rightPlayers": ["TAKA.S"],
        "theme": "SCRATCH"
      },
      {
        "type": "2v2",
        "leftPlayers": ["LOOT", "VENUS"],
        "rightPlayers": ["HINO38", "YUNA"],
        "theme": "CHARGE NOTES"
      }
    ]
  }
}
```

**颜色说明：** 只需提供 `primary`（主色）和 `secondary`（文字色），背景渐变会自动从主色生成。

### SCORE - 更新分数

```json
{
  "cmd": "score",
  "data": {
    "round": 1,
    "leftScore": 2,
    "rightScore": 0
  }
}
```

**注意：** 收到 `score` 后，该回合的选手名会从 `???` 动画揭示为真实姓名。

### RESET - 重置

```json
{ "cmd": "reset" }
```

详细协议文档：[PROTOCOL.md](./PROTOCOL.md)

## Python 使用示例

```python
import websocket
import json

ws = websocket.create_connection("ws://localhost:8080")

# 初始化比赛
ws.send(json.dumps({
    "cmd": "init",
    "data": {
        "stageName": "レギュラーステージ",
        "matchNumber": 1,
        "leftTeam": {
            "name": "TEAM A",
            "logo": "🔥",
            "colors": {
                "primary": "#ff6b6b",      # 只需主色
                "secondary": "#ffffff"     # 文字颜色
            }
        },
        "rightTeam": {
            "name": "TEAM B",
            "logo": "❄️",
            "colors": {
                "primary": "#4ecdc4",
                "secondary": "#ffffff"
            }
        },
        "matches": [
            {
                "type": "1v1",
                "leftPlayers": ["Player1"],
                "rightPlayers": ["Player2"],
                "theme": "SCRATCH"
            },
            {
                "type": "2v2",
                "leftPlayers": ["P1", "P2"],
                "rightPlayers": ["P3", "P4"],
                "theme": "2V2 BATTLE"
            }
        ]
    }
}))

# 更新第一回合分数（选手名会显示出来）
ws.send(json.dumps({
    "cmd": "score",
    "data": { "round": 1, "leftScore": 3, "rightScore": 1 }
}))

ws.close()
```

## 动态颜色系统

计分板会自动根据队伍的 `primary` 颜色生成：

- **总分行背景** - 基于主色的渐变
- **比赛行背景** - 左右队伍颜色渐变过渡
- **选手区域背景** - 半透明的主色渐变
- **边框和装饰** - 使用主色

示例：
- 银色 (`#c0c0c0`) → 深灰到浅灰渐变
- 金色 (`#ffd700`) → 深金到浅金渐变
- 红色 (`#ff6b6b`) → 深红到浅红渐变

## 在 OBS 中使用

1. 添加 **浏览器源**
2. URL: `file:///path/to/index.html` 或 `http://localhost:3000`
3. 宽度: `1920`，高度: `1080`
4. 可选：在 URL 后加 `?debug=1` 显示调试面板

## 文件结构

```
.
├── index.html          # 主页面（1920x1080 固定尺寸）
├── style.css           # 样式文件
├── app.js              # 应用程序逻辑
├── websocket-server.js # Node.js WebSocket 服务器
├── PROTOCOL.md         # 完整协议文档
├── testbench/          # Python 测试工具
│   ├── server.py       # Python WebSocket 服务器
│   ├── testbench.py    # 测试控制台
│   ├── data.json       # 队伍数据
│   └── requirements.txt
└── example/            # 示例图片
```

## 调试模式

在 URL 后添加 `?debug=1` 可显示 WebSocket 消息调试面板：

```
file:///path/to/index.html?debug=1
```

## 依赖

### 前端
- 纯 HTML/CSS/JavaScript，无需构建

### 服务器（任选其一）
- **Python**: `pip install websockets`
- **Node.js**: `npm install ws`

## License

MIT

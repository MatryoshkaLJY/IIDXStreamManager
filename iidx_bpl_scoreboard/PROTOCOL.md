# BPL Scoreboard WebSocket 协议文档

## 连接地址

```
ws://localhost:8080
```

## 指令格式

所有指令均以 JSON 格式发送：

```json
{
  "cmd": "指令名",
  "data": { ... }
}
```

---

## 1. INIT - 初始化比赛

初始化队伍信息、比赛场次和人员安排。

**请求格式：**

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
      },
      {
        "type": "1v1",
        "leftPlayers": ["IGW."],
        "rightPlayers": ["KUREI"],
        "theme": "SPEED CHANGE"
      }
    ]
  }
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `stageName` | string | 比赛阶段名称 |
| `matchNumber` | number | 第几场比赛 |
| `leftTeam` / `rightTeam` | object | 队伍信息 |
| `leftTeam.name` | string | 队伍名称 |
| `leftTeam.logo` | string | 队伍图标（emoji） |
| `leftTeam.colors` | object | 队伍配色（见下方说明） |
| `matches` | array | 比赛场次列表 |
| `matches[].type` | string | `"1v1"` 或 `"2v2"` |
| `matches[].leftPlayers` | array | 左队选手名（1或2个） |
| `matches[].rightPlayers` | array | 右队选手名（1或2个） |
| `matches[].theme` | string | 本局比赛主题 |

### 颜色配置说明

只需提供两种颜色，其他视觉效果会自动生成：

```json
{
  "colors": {
    "primary": "#c0c0c0",      // 主色 - 用于队伍名称、边框、背景渐变
    "secondary": "#ffffff"     // 次要色 - 用于总分数字、选手名
  }
}
```

**自动生成：**
- `accent` - 强调色（从主色派生）
- `bgGradient.start` - 渐变起始色（主色变暗30%）
- `bgGradient.end` - 渐变结束色（主色变亮）

**示例颜色效果：**

| 主色 | 效果 |
|------|------|
| `#c0c0c0` (银) | 深灰 → 浅灰渐变 |
| `#ffd700` (金) | 深金 → 浅金渐变 |
| `#ff6b6b` (红) | 深红 → 浅红渐变 |
| `#4ecdc4` (青) | 深青 → 浅青渐变 |

---

## 2. SCORE - 更新分数

更新指定回合的分数，同时会**显示该回合的选手名**。

**请求格式：**

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

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `round` | number | 回合数（1-based） |
| `leftScore` | number | 左队得分 |
| `rightScore` | number | 右队得分 |

**注意：**
- 在收到该回合的 `score` 指令前，选手名会显示为 `???`
- 收到 `score` 后，选手名会以动画方式显现
- 总分会自动累加计算

---

## 3. RESET - 重置比赛

重置所有分数，选手名重新隐藏。

**请求格式：**

```json
{
  "cmd": "reset"
}
```

---

## 使用示例

### 初始化比赛

```javascript
ws.send(JSON.stringify({
  cmd: 'init',
  data: {
    stageName: 'レギュラーステージ',
    matchNumber: 1,
    leftTeam: {
      name: 'TEAM A',
      logo: '🔥',
      colors: {
        primary: '#ff6b6b',      // 只需主色
        secondary: '#ffffff'     // 文字颜色
      }
    },
    rightTeam: {
      name: 'TEAM B',
      logo: '❄️',
      colors: {
        primary: '#4ecdc4',
        secondary: '#ffffff'
      }
    },
    matches: [
      { type: '1v1', leftPlayers: ['Player1'], rightPlayers: ['Player2'], theme: 'SCRATCH' },
      { type: '2v2', leftPlayers: ['P1', 'P2'], rightPlayers: ['P3', 'P4'], theme: '2V2 BATTLE' }
    ]
  }
}));
```

### 更新第一回合分数

```javascript
ws.send(JSON.stringify({
  cmd: 'score',
  data: {
    round: 1,
    leftScore: 3,
    rightScore: 1
  }
}));
// 此时第一回合的选手名会显示出来
```

### Python 示例

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
            "name": "SILK HAT",
            "logo": "🎩",
            "colors": {
                "primary": "#c0c0c0",      # 主色
                "secondary": "#ffffff"     # 次要色
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
                "leftPlayers": ["LOOT", "IGW."],
                "rightPlayers": ["HINO38", "KUREI"],
                "theme": "CHARGE NOTES"
            }
        ]
    }
}))

# 更新分数
ws.send(json.dumps({
    "cmd": "score",
    "data": {
        "round": 1,
        "leftScore": 2,
        "rightScore": 0
    }
}))

ws.close()
```

---

## 计分板显示逻辑

1. **收到 `init`**：
   - 显示队伍信息
   - 根据 `colors.primary` 自动生成背景渐变
   - 生成比赛场次行
   - 选手名显示为 `???`（隐藏）
   - 分数显示为 `-`（隐藏）

2. **收到某回合的 `score`**：
   - 更新该回合分数
   - 以动画方式显示选手名
   - 自动重新计算并更新总分

3. **收到 `reset`**：
   - 所有分数清零
   - 选手名重新隐藏

---

## 动态样式说明

计分板使用 CSS 变量系统，会根据队伍主色自动调整：

```css
/* 生成的 CSS 变量示例 */
--left-primary: #c0c0c0;      /* 提供的主色 */
--left-secondary: #ffffff;    /* 提供的次要色 */
--left-bg-start: #3a3a3a;     /* 自动生成：主色 * 0.3 */
--left-bg-end: #5a5a5a;       /* 自动生成：主色变亮 */
```

**应用位置：**
- 总分行背景渐变
- 比赛行左右渐变背景
- 选手区域半透明背景
- 边框、分隔线
- 文字阴影

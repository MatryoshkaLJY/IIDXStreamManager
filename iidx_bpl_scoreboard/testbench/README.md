# BPL Scoreboard Testbench

Python 测试工具，用于通过 WebSocket 向计分板发送指令。

## 安装依赖

```bash
cd testbench
pip install -r requirements.txt
```

## 使用方式

### 1. 交互模式（推荐）

```bash
python testbench.py
```

菜单选项：
- `init` - 初始化新比赛（选择队伍、模板）
- `score` - 更新回合分数
- `reset` - 重置所有分数
- `quick` - 随机快速开始
- `demo` - 自动运行完整演示
- `list` - 列出所有队伍/模板

### 2. 命令行模式

```bash
# 运行自动演示
python testbench.py --demo

# 初始化指定队伍比赛
python testbench.py --init silk_hat,game_panic

# 使用特定模板
python testbench.py --init round1,apa --template standard_5round
```

### 3. Python API

```python
import asyncio
from testbench import Testbench

async def main():
    tb = Testbench()

    # 连接 WebSocket
    await tb.client.connect()

    # 生成比赛
    match = tb.generator.generate(
        left_team_id="silk_hat",
        right_team_id="game_panic",
        template_id="standard_4round"
    )

    # 发送初始化
    await tb.client.send_init(match)

    # 更新分数
    await tb.client.send_score(1, 2, 0)
    await tb.client.send_score(2, 3, 1)

    # 断开
    await tb.client.disconnect()

asyncio.run(main())
```

## 数据文件结构

`data.json` 包含：

- `teams` - 所有队伍信息（名称、图标、配色、选手）
- `themes` - 比赛主题池
- `match_templates` - 比赛模板（回合数、类型）
- `stages` - 比赛阶段名称
- `season_schedule` - 完整赛季赛程表

## 扩展数据

添加新队伍到 `data.json`：

```json
{
  "teams": {
    "new_team": {
      "id": "new_team",
      "name": "NEW TEAM",
      "logo": "🔥",
      "colors": {
        "primary": "#ff6b6b",
        "secondary": "#ffffff"
      },
      "players": [
        {"id": "p1", "name": "PLAYER1", "role": "veteran"},
        {"id": "p2", "name": "PLAYER2", "role": "regular"}
      ]
    }
  }
}
```

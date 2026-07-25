# iidx_director — IIDX 赛事导播台

街机 beatmania IIDX 赛事直播的顶层导播控制应用。导播通过网页逐步确认驱动整场比赛：
导入赛程 → 回合准备（分配机台）→ 确认开始 → 自动抓分判胜负 → 确认写入记分板。

替代旧的 `iidx_tpl_manager`（保留不动，本模块独立重写）。

## 支持的比赛类型

- **团队赛（BPL）**：双方队伍、队员名单、每回合 1v1/2v2 安排与分值，推送到 BPL 记分板（WS 8080）。
- **个人淘汰赛**：16 人分 A-D 组，每组 4 局，自动推演晋级（半决赛 E/F 组、决赛对阵与平局决胜），推送到淘汰赛记分板（WS 8081）。

## 启动

```bash
cd iidx_director
source ../.venv/bin/activate
python -m src.app            # 导播台 @ http://localhost:5003，并自动拉起本地基础服务
```

首次创建环境：

```bash
cd <monorepo>
python -m venv .venv
.venv/bin/python -m pip install Flask Flask-SocketIO pydantic obsws-python websockets Pillow numpy PyYAML opencv-python onnxruntime pytest
```

导播台会自动启动本仓库内的状态识别（9876）、分数识别（9877）、两个记分板 relay（8080/8081）
和场景信息 relay（8082）。如果端口已经有服务监听，则直接复用，退出时不会停止已存在的外部服务。
状态机由 `obs_manager` 在进程内加载。仍需手动运行 OBS Studio（WS 4455）。
调试时可使用 `python -m src.app --no-autostart` 禁用自动启动。OBS 密码用环境变量
`IIDX_OBS_PASSWORD` 或在设置页输入（不入盘）。

## 使用流程

1. **设置 / 赛程**：连接 OBS → 选择比赛类型 → 上传赛程 JSON（可先下载模板编辑）→「开始比赛」（自动向记分板发 init）→ 启动机台监控。
2. **回合准备**：页面显示当前回合对阵（队名/选手/主题/分值），为每个选手选择机台和 1P/2P 侧，「确认开始」→ 切 OBS 场景 + 推送场景信息 + 进入抓分。
3. **比分确认**：状态机抓到结果画面后自动带入各选手 EX 分并判定胜负；确认页显示每台参赛机台的成绩截图，导播可改分后「切换计分板并写入」→ 切到计分板场景 → 等待 5 秒 → 推送记分板 →「进入下一回合」。
   - 抓分失败时可点「手动录入」直接输入分数进入确认。
   - 推送失败时比分确认页提供「重试推送」。
4. **场景快捷切换**：顶部会根据设置中的场景配置显示现场、比赛、计分板等快捷按钮；进入下一回合不会自动切 OBS 场景。

赛程 JSON 格式见 `data/team_match.json` / `data/knockout.json`（首次启动自动生成模板），
上传时校验失败会给出具体原因，旧文件自动备份为 `.bak`。

## 场景信息（OBS 浏览器源）

`sceneinfo/overlay.html` 是固定 `1920×1080` 的 OBS 浏览器源，使用
`sceneinfo/manifest.json` 和 `sceneinfo/assets/` 中由 PSD 导出的五套布局：
`dp_arena`、`dp_bpl`、`sp_arena`、`sp_bpl`、`live`。PSD 源文件在项目外部的设计目录中保存，
可用 `python sceneinfo/export_psd_templates.py --source <PSD目录>` 重新导出资源。

场景网页通过 `ws://localhost:8082` 接收消息。协议：

- `round_start`：`{mode, round: {...}, entries: [{player, machine, side, team, color}]}`
- `round_result`：`{mode, round: {...}, result: {scores, ...}}`
- `match_end`：`{mode, rounds?/final_ranking?}`

三个现有命令的 `data` 可带 `template` 和 `texts` 字段。外部程序也可以发送文字覆盖：

```json
{
  "cmd": "set_text",
  "data": {
    "template": "dp_bpl",
    "values": {"left_team_name": "队伍 A", "right_points": "2PT"}
  }
}
```

可替换字段以 `sceneinfo/manifest.json` 中各模板的 `layers[].id` 为准。非文字图层（Logo、角色、
装饰和游戏画面框）会以独立 PNG 图层叠放；文字图层以独立 DOM 图层渲染。

名为 `红板`、`红名板`、`红板长` 的图层带有独立 `hueKey`，可以发送 hue 调整：

```json
{
  "cmd": "set_hue",
  "data": {
    "template": "dp_bpl",
    "values": {"all": 120}
  }
}
```

正式场景网页实现后直接替换 `sceneinfo/overlay.html`，协议不变。

## 测试

```bash
cd iidx_director
python -m pytest tests -q          # 单元/路由测试（mock OBS/WS）
python sceneinfo/smoke_test.py     # 端到端 smoke：真 app + 真 relay 走一回合
```

## 结构

```
src/config/    赛程 pydantic 模型 + 加载/模板（路径锚定模块目录）
src/match/     会话状态机（IDLE→PREP→LIVE→REVIEW→PUSHED→MATCH_END）、计分、淘汰赛推演
src/obs/       OBS 场景控制（单连接）+ 机台监控（复用 obs_manager.OBSManager）
src/push/      记分板推送（8080/8081）+ 场景信息推送（8082）
src/app.py     Flask + SocketIO 路由编排（端口 5003）
sceneinfo/     8082 WS 中继 + PSD 场景 overlay.html + 导出脚本 + smoke_test.py
data/          赛程 JSON（模板自动生成）
tests/         pytest
```

## 注意

- 淘汰赛晋级/平局决胜规则复刻自 `iidx_knockout_scoreboard/app.js`（PT 2/1/0/0，并列按总 EX，
  决赛 PT 并列进入加赛）；决赛 score/settle 的 group 必须是 `"finals"`。
- 分数服务返回键为 `1pscore`/`2pscore`（无下划线）。
- 1v1 EX 平分判 0:0、2v2 同分按分配顺序，导播均可在确认前改分修正。
- 比赛会话存于内存，重启 app 进度丢失（比分以记分板为准）。

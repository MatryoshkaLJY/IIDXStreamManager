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
和 OBS overlay relay（8082）。如果端口已经有服务监听，则直接复用，退出时不会停止已存在的外部服务。
状态机由 `obs_manager` 在进程内加载。仍需手动运行 OBS Studio（WS 4455）。
调试时可使用 `python -m src.app --no-autostart` 禁用自动启动。OBS 密码用环境变量
`IIDX_OBS_PASSWORD` 或在设置页输入（不入盘）。

## 使用流程

1. **设置 / 赛程**：连接 OBS → 选择比赛类型 → 上传赛程 JSON（可先下载模板编辑）→「开始比赛」（自动向记分板发 init）→ 启动机台监控。
2. **回合准备**：页面显示当前回合对阵（队名/选手/主题/分值），为每个选手选择机台和 1P/2P 侧，「确认开始」→ 切 OBS 场景 + 推送 overlay 信息 + 进入抓分。
3. **比分确认**：状态机抓到结果画面后自动带入各选手 EX 分并判定胜负；确认页显示每台参赛机台的成绩截图，导播可改分后「切换计分板并写入」→ 切到计分板场景 → 等待 5 秒 → 推送记分板 →「进入下一回合」。
   - 抓分失败时可点「手动录入」直接输入分数进入确认。
   - 推送失败时比分确认页提供「重试推送」。
4. **场景快捷切换**：顶部会根据设置中的场景配置显示现场、比赛、计分板等快捷按钮；进入下一回合不会自动切 OBS 场景。

默认 OBS 场景名映射为：团队赛 1V1 使用 `SP_BPL` / `DP_BPL`，团队赛 2V2 和个人赛使用
`SP_Arena` / `DP_Arena`，现场摄像使用 `Live`。网页按钮上的 SP/DP、1V1/2V2 是逻辑标签，
不会作为 OBS 场景名发送。

开发端没有机台采集卡时，可在设置页启用「开发测试模式」。OBS 连接和场景快捷切换仍然有效，只有机台
画面监控/状态识别会被跳过。开始回合后，在「比分确认」页按机台填写
1P/2P 分数并提交；导播台会走与真实监控相同的出分回调、自动进入 REVIEW，并为该机台保存一张空白 PNG
成绩截图。测试模式也提供接口：

```json
POST /api/test/scores
{"machine_id": "IIDX#1", "scores": {"1p": 2000, "2p": 1500}}
```

赛程 JSON 格式见 `data/team_match.json` / `data/knockout.json`（首次启动自动生成模板），
上传时校验失败会给出具体原因，旧文件自动备份为 `.bak`。
两种赛程都可在顶层指定 `"playType": "SP"` 或 `"playType": "DP"`；缺省时按 SP 兼容旧配置。
顶层字段示例：

```json
{
  "playType": "DP",
  "stageName": "レギュラーステージ",
  "matchNumber": 1
}
```

## OBS Overlay

`overlay/obs-overlay.html` 是固定 `1920×1080` 的 OBS 浏览器源，包含
`dp-arena`、`dp-bpl`、`sp-arena`、`sp-bpl` 四套布局及其 PNG/字体资源。
OBS 可使用 `http://localhost:5003/overlay/?preset=sp-bpl`，也可直接打开该 HTML；画布默认透明。

场景网页通过 `ws://localhost:8082` 接收消息。协议：

- `round_start`：`{mode, round: {...}, entries: [{player, machine, side, team, color}]}`
- `round_result`：`{mode, round: {...}, result: {scores, ...}}`
- `match_end`：`{mode, rounds?/final_ranking?}`

三个命令的 `data` 可带 `template`、`texts` 和 `hues` 字段。外部程序也可以发送文字覆盖：

```json
{
  "cmd": "set_text",
  "data": {
    "template": "dp_bpl",
    "values": {"left_team_name": "队伍 A", "right_points": "2PT"}
  }
}
```

文字字段使用语义化名称：`header_round`、`header_theme`、`left_team_name`、
`right_team_name`、`left_player`、`right_player`、`left_points`、`right_points`，
以及个人赛的 `machine_1_player` 至 `machine_4_player`。

团队赛 1V1 的 BPL 模板使用 `left` / `right`，作用于对应一侧的背景板；团队赛 2V2
切换到 Arena 模板，并按机台分配发送 `machine_1` 至 `machine_4`，其 Hue 与所属队伍颜色一致。
个人赛 Hue 固定绑定机台：1 号机红色 `0deg`、2 号机黄色 `60deg`、3 号机绿色 `120deg`、
4 号机蓝色 `240deg`。

也可以直接发送 Hue 调整：

```json
{
  "cmd": "set_hue",
  "data": {
    "template": "dp_bpl",
    "values": {"left": 120, "right": 240}
  }
}
```

## 测试

```bash
cd iidx_director
python -m pytest tests -q          # 单元/路由测试（mock OBS/WS）
python overlay/smoke_test.py      # 端到端 smoke：真 app + 真 relay 走一回合
```

## 结构

```
src/config/    赛程 pydantic 模型 + 加载/模板（路径锚定模块目录）
src/match/     会话状态机（IDLE→PREP→LIVE→REVIEW→PUSHED→MATCH_END）、计分、淘汰赛推演
src/obs/       OBS 场景控制（单连接）+ 机台监控（复用 obs_manager.OBSManager）
src/push/      记分板推送（8080/8081）+ OBS overlay 推送（8082）
src/app.py     Flask + SocketIO 路由编排（端口 5003）
overlay/       OBS overlay.html、PNG/字体资源、8082 WS 中继 + smoke_test.py
data/          赛程 JSON（模板自动生成）
tests/         pytest
```

## 注意

- 淘汰赛晋级/平局决胜规则复刻自 `iidx_knockout_scoreboard/app.js`（PT 2/1/0/0，并列按总 EX，
  决赛 PT 并列进入加赛）；决赛 score/settle 的 group 必须是 `"finals"`。
- 分数服务返回键为 `1pscore`/`2pscore`（无下划线）。
- 1v1 EX 平分判 0:0、2v2 同分按分配顺序，导播均可在确认前改分修正。
- 比赛会话存于内存，重启 app 进度丢失（比分以记分板为准）。

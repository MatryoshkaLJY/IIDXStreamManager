# IIDX Stream Manager

beatmania IIDX 赛事直播工具集。当前生产入口是 **iidx_director**：导播通过网页导入赛程、分配机台、确认回合、抓取成绩、复核比分，并将确认后的结果推送到 OBS overlay 和记分板。

旧的 iidx_tpl_manager 仅作为历史模块保留；streamlit-app 和 iidx_stream_state_machine 已移除。

## 生产导播台

iidx_director 是 Flask + Flask-SocketIO 应用，默认运行在 http://127.0.0.1:5003/。它负责：

- 团队赛（BPL）和个人淘汰赛的赛程加载、Pydantic 校验与模板生成；
- 团队赛 1v1 / 2v2、抢夺赛、EX/BP 判定和决赛三局配置；
- 16 人淘汰赛 A-D → E/F → 决赛；
- 8 人 EF 赛制和 4 人直接决赛；
- 每个回合的选手到机台、1P/2P 侧分配；
- 多机台成绩截图、分数识别、手动补录、重抓和推送重试；
- OBS 场景切换、源可见性、overlay 文字/Hue 覆盖；
- 可选的团队赛 1v1 串口音频切换。

### 回合状态

    IDLE -> PREP -> LIVE -> REVIEW -> PUSHED
                             |          |
                             +----------+-> 下一回合 PREP / MATCH_END

导播在 PREP 分配机台并确认开始；LIVE 阶段由导播手动点击“抓取所有机台分数”，不再依赖已弃用的状态识别模型自动判断游玩状态；REVIEW 阶段可修正识别结果，只有确认后才写入记分板。

## 快速启动

### Linux / macOS

在仓库根目录创建环境并安装依赖：

    python3 -m venv .venv
    .venv/bin/python -m pip install Flask Flask-SocketIO pydantic obsws-python websockets Pillow numpy PyYAML opencv-python onnxruntime pytest

启动 OBS Studio（WebSocket 5，默认端口 4455），然后启动导播台：

    cd iidx_director
    ../.venv/bin/python -m src.app

导播台会自动启动未占用的本地成绩识别服务、两个记分板 relay 和 overlay relay。已有监听端口会被复用，不会被导播台接管或退出。调试时可禁用自动启动：

    ../.venv/bin/python -m src.app --no-autostart

OBS 密码使用环境变量 IIDX_OBS_PASSWORD 或在设置页输入；密码不会写入运行时状态。

### Windows 生产包

生产目录为 iidx_director_windows/，部署说明见 DEPLOY_WINDOWS.md：

    Set-ExecutionPolicy -Scope Process Bypass
    .\\install_windows.ps1
    .\\check_windows_install.ps1
    .\\start_director.bat

无机台采集卡时使用 start_director_test_mode.bat。停止由本次启动创建的服务：

    .\\stop_services.ps1

## 导播操作流程

1. 在设置页连接 OBS，选择 team、knockout、knockout_ef 或 knockout_final。
2. 上传或编辑赛程 JSON，点击开始比赛；应用会向对应记分板发送 init。
3. 在回合准备页为每位选手选择机台和 1P / 2P 侧，确认开始并应用场景事务。
4. 比赛结束后点击抓分；成绩服务读取截图中的 EX 分，BP 回合读取 miss count。
5. 在比分确认页检查截图和结果，可手动修改缺失或错误分数。
6. 确认推送后写入记分板并进入下一回合；推送失败可重试。

开发测试模式会跳过机台监控，可通过接口注入成绩：

    POST /api/test/scores
    {"machine_id":"IIDX#1","scores":{"1p":2000,"2p":1500}}

## OBS 与服务端口

| 端口 | 服务 | 说明 |
| ---: | --- | --- |
| 4455 | OBS Studio WebSocket | 外部依赖 |
| 5003 | iidx_director | 导播网页、API、Socket.IO |
| 8080 | BPL scoreboard relay | 团队赛记分板 |
| 8081 | knockout scoreboard relay | 淘汰赛记分板 |
| 8082 | overlay relay | OBS overlay 消息 |
| 9877 | iidx_score_reco | 成绩/BP TCP 识别服务 |
| 9876 | iidx_state_reco | 已弃用，不自动启动，保留备用 |

浏览器源统一从导播台提供：

    http://127.0.0.1:5003/overlay/
    http://127.0.0.1:5003/scoreboard/bpl/
    http://127.0.0.1:5003/scoreboard/knockout/

所有浏览器源按 1920x1080 配置；overlay 使用透明背景。

## 赛程配置

配置文件位于 iidx_director/data/，上传时会校验，旧文件备份为 .bak：

| 文件 | 模式 | 结构 |
| --- | --- | --- |
| team_match.json | team | 双队、回合、选手、主题、分值 |
| knockout.json | knockout | A-D 四组 16 人 |
| knockout_ef.json | knockout_ef | E/F 两组 8 人 |
| knockout_final.json | knockout_final | finals 组 4 人 |

团队赛顶层可设置 playType 为 SP 或 DP。团队回合支持 1v1、2v2、judgeBy: ex 或 1v1 专用的 judgeBy: bp。前 grabRounds 回合为抢夺赛，不写入记分板；结束后导播录入奖励 PT。

淘汰赛每局按竞争排名计算 PT 2/1/0/0。A-D 组第 2/3 名跨线且 PT、总 EX 均相同时加赛；决赛任意 PT 并列都加赛。Python 逻辑与 iidx_knockout_scoreboard/app.js 保持一致。

## Overlay 与协议

Overlay 页面和资源在 iidx_director/overlay/，模板包括 sp-bpl、dp-bpl、sp-arena、dp-arena。overlay relay（ws://127.0.0.1:8082）接收 round_start、round_result、match_end、set_text 和 set_hue。

记分板通过 JSON WebSocket 接收 init、score、settle、reset。协议细节见 iidx_bpl_scoreboard/PROTOCOL.md 和 iidx_director/README.md。

## 目录结构

    iidx_director/             生产导播台、赛程、overlay、测试
    iidx_bpl_scoreboard/       BPL 团队赛浏览器源与 relay
    iidx_knockout_scoreboard/  个人淘汰赛浏览器源与 relay
    iidx_score_reco/           OpenCV 成绩/BP 识别服务
    iidx_state_reco/           已弃用的 ONNX 状态识别服务
    iidx_state_machine/        状态机实现，供 obs_manager 进程内使用
    obs_manager/               OBS 截图与识别封装
    iidx_tpl_manager/          旧版导播台，暂不维护
    iidx_tpl_design_rules/     overlay 设计规格

模块通过 TCP、WebSocket 和文件配置协作。除 obs_manager 加载状态机、iidx_director 使用 obs_manager 外，不依赖跨目录 Python 导入。

## 测试

    cd iidx_director
    pytest
    cd ..
    python test_knockout_integration.py
    cd iidx_knockout_scoreboard
    node app.test.js

iidx_director 测试默认 mock OBS、WebSocket 和外部服务；集成脚本覆盖 16 人、EF 和 4 人决赛状态流转。

## 相关文档

- iidx_director/README.md：导播台 API、overlay 和配置细节
- DEPLOY_WINDOWS.md：Windows 安装、启动、OBS 源和故障排查
- iidx_bpl_scoreboard/PROTOCOL.md：BPL 记分板协议
- AGENTS.md：仓库结构、端口和维护约定

## 许可证

MIT

# iidx_director

IIDX 赛事生产导播台。网页端由 Flask + Flask-SocketIO 提供，默认监听 127.0.0.1:5003。

## 作用

- 导入并校验团队赛、16 人淘汰赛、8 人 EF 赛制和 4 人决赛赛程；
- 按回合为选手分配机台与 1P/2P 侧；
- 控制 OBS 场景、源可见性和 1920x1080 overlay；
- 手动并行抓取机台成绩截图，调用 iidx_score_reco 识别 EX/BP；
- 在 REVIEW 页面补录或修正成绩，确认后推送 scoreboard；
- 管理团队赛抢夺赛、BP 判定、淘汰赛晋级和决赛加赛；
- 可选通过串口把直播音频切到当前左队选手的机台。

## 启动

在仓库根目录准备虚拟环境后：

    cd iidx_director
    ../.venv/bin/python -m src.app

默认会自动启动未占用的本地服务：

| 端口 | 服务 |
| ---: | --- |
| 5003 | 导播台网页和 API |
| 8080 | BPL scoreboard relay |
| 8081 | knockout scoreboard relay |
| 8082 | overlay relay |
| 9877 | score recognition TCP service |

9876 的状态识别服务已经弃用，不会自动启动。已有端口会被复用；调试时使用：

    ../.venv/bin/python -m src.app --no-autostart

外部依赖是 OBS Studio WebSocket 5（4455）。密码通过 IIDX_OBS_PASSWORD 或设置页提供。

## 比赛流程

    IDLE -> PREP -> LIVE -> REVIEW -> PUSHED -> 下一回合 / MATCH_END

1. 设置页连接 OBS，选择模式并上传 JSON 赛程。
2. 开始比赛，导播台向对应 scoreboard 发送 init。
3. PREP 分配机台和 1P/2P，确认后应用场景事务和 overlay。
4. LIVE 点击抓分；抓分失败也会进入 REVIEW，允许手动录入。
5. REVIEW 检查截图、成绩和判定，确认后推送 score/settle。
6. 推送失败可 repush，完成后 advance 到下一回合。

会话状态保存在内存；重启导播台不会恢复当前回合，记分板数据需另行保留。

## 模式和配置

配置目录：iidx_director/data/

| 文件 | 模式 | 规则 |
| --- | --- | --- |
| team_match.json | team | BPL 团队赛，支持 1v1/2v2、抢夺赛和 BP 判定 |
| knockout.json | knockout | A-D 四组，晋级 E/F 后进入 finals |
| knockout_ef.json | knockout_ef | E/F 两组直接开始的 8 人赛 |
| knockout_final.json | knockout_final | finals 组直接开始的 4 人赛 |

所有上传配置先由 Pydantic 校验，旧文件改名为 .bak。团队赛的 judgeBy: bp 只允许 1v1；playType 支持 SP 和 DP。

淘汰赛 Python 规则必须与 iidx_knockout_scoreboard/app.js 保持一致：小组 PT 为 2/1/0/0，A-D 只有跨越第 2/3 名出线线的完全并列才加赛，决赛任意 PT 并列都加赛。

## OBS 源

    http://127.0.0.1:5003/overlay/
    http://127.0.0.1:5003/scoreboard/bpl/
    http://127.0.0.1:5003/scoreboard/knockout/

浏览器源固定 1920x1080；overlay 使用透明背景。默认场景名和映射可在设置页调整。

## 串口音频切换

导播台通过 pyserial 向外部设备发送 ASCII 数字 1-4：数字对应 1-4 号机台音频输入。团队赛 1v1 点击开始回合时，会从左队选手的机台 ID（例如 IIDX#2）提取编号并自动发送；顶部也提供音源 1-4 快捷按钮。

设置页保存 enabled、port、baudrate（默认 9600）和 timeout。发送失败会在页面显示 notice，并自动重试一次。设备固件和硬件实现见：

    https://github.com/MatryoshkaLJY/Pico-quad-audio-switch

## API 要点

所有业务错误返回 HTTP 200 和 success: false。常用接口：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | /api/obs/connect | 连接 OBS |
| POST | /api/config/upload | 上传 team/knockout 配置 |
| POST | /api/match/start | 开始比赛 |
| POST | /api/round/assign | 保存机台分配 |
| POST | /api/round/begin | 开始回合 |
| POST | /api/scores/capture | 抓取所有机台成绩 |
| POST | /api/round/confirm | 确认并推送比分 |
| POST | /api/round/repush | 重试最近一次推送 |
| POST | /api/serial-audio/switch | 手动发送音频源编号 |
| POST | /api/test/scores | 测试模式注入成绩 |

overlay relay（8082）接收 round_start、round_result、match_end、set_text 和 set_hue。scoreboard relay 分别使用 8080 和 8081，协议见 ../iidx_bpl_scoreboard/PROTOCOL.md。

## 测试

    cd iidx_director
    pytest
    cd ..
    python test_knockout_integration.py

测试 mock OBS、WebSocket 和外部推理服务；集成脚本覆盖 16 人、EF 和 4 人决赛。

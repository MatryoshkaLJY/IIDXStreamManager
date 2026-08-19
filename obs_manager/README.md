# obs_manager

OBS WebSocket、截图和推理服务的 Python 封装。iidx_director 使用其中的 OBSManager/CabinetMonitor 处理机台连接与截图；旧的自动状态轮询接口保留用于调试。

## 能力

- 连接 OBS Studio WebSocket 5（4455）；
- 抓取指定视频源的 PNG/JPEG；
- 调用 iidx_score_reco 识别成绩；
- 可选调用 iidx_state_reco 并驱动 iidx_state_machine；
- 为多台机台维护独立连接和配置。

## 使用

    python obs_manager.py --host 127.0.0.1 --port 4455 --password PASSWORD --source video

代码调用从 obs_manager import OBSManager，然后使用 capture_source、capture_and_recognize_score、register_machine 和 process_frame。成绩服务返回键使用 1pscore/2pscore 等无下划线名称。

## 相关服务

| 服务 | 地址 | 状态 |
| --- | --- | --- |
| OBS | 127.0.0.1:4455 | 必需 |
| score reco | 127.0.0.1:9877 | 导播台生产依赖 |
| state reco | 127.0.0.1:9876 | 已弃用，备用 |
| state machine | 进程内或 9999 | 旧自动流程/调试 |

## 测试

    python test_obs_manager.py
    python test_score_reco.py

测试默认使用 mock，不需要运行 OBS。

# IIDX 导播台 Windows 部署指南

本包的根目录固定为 `iidx_director_windows`，目标环境为 Windows 10/11 x64、Python 3.12 x64 和 OBS Studio 28+（OBS WebSocket 5）。请把目录解压到普通工作目录，例如 `C:\IIDX\iidx_director_windows`，不要放在 `C:\Program Files` 等受保护目录，也不要改动目录层级。

## 安装

1. 安装 Python 3.12 x64，安装时勾选 **Add Python to PATH**。
2. 安装 OBS Studio，并在 OBS 的 WebSocket 设置中启用服务器：端口 `4455`。密码可以设置，但不要写入包文件；运行时在导播台页面输入，或设置环境变量 `IIDX_OBS_PASSWORD`。
3. 在包根目录右键 PowerShell，执行：

   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\install_windows.ps1
   .\check_windows_install.ps1
   ```

安装脚本会创建 `.venv`、在线安装固定版本依赖、检查 ONNX 模型、字体模板、ROI 和状态机文件，并生成干净的 `data/` 与 `runtime/` 目录。

## OBS 场景与浏览器源

导播台默认使用以下场景名，请在 OBS 中保持一致，或在设置页面修改映射：`SP_BPL`、`SP_Arena`、`DP_BPL`、`DP_Arena`、`Live`、`Team_Scoreboard`、`Knockout_Scoreboard`。团队赛切换到 `Team_Scoreboard`，个人淘汰赛切换到 `Knockout_Scoreboard`。
赛程 JSON 顶层可用 `"playType": "SP"` 或 `"playType": "DP"` 指定整场游玩类型；未填写时默认 SP。

浏览器源建议使用 HTTP 地址（无需 `file:///`）：

| 用途 | URL |
| --- | --- |
| OBS overlay | `http://127.0.0.1:5003/overlay/` |
| BPL scoreboard | `http://127.0.0.1:5003/scoreboard/bpl/` |
| Knockout scoreboard | `http://127.0.0.1:5003/scoreboard/knockout/` |

所有源设置为 1920×1080，启用透明背景（overlay），并允许源在不可见时继续运行。记分板页面会自动连接本机 WebSocket relay。

## 启动与首次配置

运行 `start_director.bat`，导播台会启动状态识别 `9876`、分数识别 `9877`、BPL relay `8080`、Knockout relay `8081`、overlay relay `8082` 和 Flask 页面 `5003`。打开 `http://127.0.0.1:5003/`，先连接 OBS，再上传或编辑赛程配置，确认机台视频源名称和场景映射。

真实监控模式会从 OBS 抓图并调用两个识别服务。`start_director_test_mode.bat` 设置测试模式，只使用页面注入成绩，不要求机台采集链路；OBS 仍可连接以测试切场景。

### 串口音频切换（团队赛 1V1）

如需在团队赛 1V1 回合开始时自动把直播音频切到左队选手机台，可在设置页启用「串口音频切换」：

1. 将外部音频切换设备的串口线接到导播 PC；
2. 在设置页选择对应串口（如 `COM3`）并保持默认波特率 `9600`；
3. 勾选「团队赛1V1自动切换」并保存。

启用后，每次团队赛 1V1 回合点击「创建开始待应用」时，导播台会从机台 ID（如 `IIDX#2`）提取编号并通过串口发送 `2`，音频切换设备需能接收 1-4 的 ASCII 数字并切换对应输入源。

停止时执行 `stop_services.ps1`。该脚本只结束本次导播台进程树，不会关闭外部 OBS；手动启动且未由导播台创建的服务也不会被接管。

## 回环端口与防火墙

业务服务默认只绑定 `127.0.0.1`：`5003`、`8080`、`8081`、`8082`、`9876`、`9877`。通常无需开放入站防火墙规则；OBS WebSocket 使用外部程序的 `4455`，也建议仅允许本机访问。

## 故障排查

- **Python 不在 PATH**：重新安装 3.12 x64 并勾选 PATH，或在 PowerShell 中确认 `python --version`。
- **依赖安装失败**：确认业务 PC 可以访问 PyPI；删除 `.venv` 后重新运行安装脚本。
- **ONNX Runtime 加载失败**：确认使用 64 位 Python、模型三件套完整，且没有把 `classifier_augmented_medium.onnx.data` 改名。
- **端口被占用**：运行 `check_windows_install.ps1`，关闭占用进程后再启动；不要修改保留端口。
- **OBS 连接失败**：确认 OBS WebSocket 5 已启用、端口为 `4455`，密码与导播台输入一致。
- **浏览器源未连接**：先确认 `http://127.0.0.1:5003/` 可访问，再检查 relay 端口和 OBS 源的 URL 是否带结尾 `/`。
- **识别服务未启动**：查看启动窗口日志，重点检查模型、字体、`rois.csv` 和 OpenCV/ONNX Runtime 错误。

## 校验、升级与备份

包内 `SHA256SUMS.txt` 列出所有文件的 SHA-256。可在 PowerShell 中运行 `Get-FileHash -Algorithm SHA256 <文件>` 逐项核对。升级前只备份 `iidx_director\data` 和 `iidx_director\runtime`；不要把旧的 `runtime\state.json`、`.venv` 或机器密码覆盖到新包。升级后重新运行安装脚本并恢复这两个目录中的业务配置即可。

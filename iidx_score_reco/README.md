# IIDX Score Recognizer - TCP Service

从 IIDX 游戏结算画面截图中自动识别 SCORE 等数字。支持 TCP 协议，接收图像字节流，返回 JSON 格式识别结果。

## 依赖安装

```bash
pip install opencv-python numpy pillow
```

## TCP 通信协议

### 连接

客户端通过 TCP 连接到服务器（默认端口 `9877`）。

### 输入格式（客户端 → 服务器）

| 字段 | 长度 | 说明 |
|------|------|------|
| 图像长度 | 4 字节 | 大端无符号整数 (uint32 big-endian) |
| 图像数据 | N 字节 | JPEG/PNG/WEBP/BMP 等格式 |

**示例：**
```
[0x00 0x00 0x10 0x00] [JPEG bytes...]  # 长度=4096 的图像
```

### 输出格式（服务器 → 客户端）

**成功响应：**
```json
{"2pbscore": "1626", "2pscore": "1234", "2pbbp": "15", "2pbp": "8"}
```

**错误响应：**
```json
{"error": "无法读取图片格式"}
```

每个 JSON 响应以换行符 `\n` 结尾。

### 通信流程

1. 客户端建立 TCP 连接到服务器
2. 客户端发送：**4字节长度头 + 图像数据**
3. 服务器接收图像，进行数字识别
4. 服务器返回：**JSON结果 + \n**
5. 连接可保持，重复步骤 2-4 进行多次识别
6. 发送长度为 0 的头部（4 字节 `0x00000000`）关闭连接

## ROI 配置

ROI 区域通过 CSV 文件配置，格式为：`name,x1,y1,x2,y2`

**示例（rois.csv）：**
```csv
2pbscore,1550,546,1704,580
2pscore,1712,546,1867,580
2pbbp,1550,615,1704,648
2pbp,1712,615,1867,648
```

### 字段说明

| 字段名 | 含义 |
|--------|------|
| `2pbscore` | 2P 后方分数 (BACK SPIN SCORE) |
| `2pscore` | 2P 前方分数 (SCORE) |
| `2pbbp` | 2P BACK SPIN BLUE BALL POINT |
| `2pbp` | 2P BLUE BALL POINT |
| `2ppg` | 2P PERFECT GREAT |
| `2pgr` | 2P GREAT |
| `2pgd` | 2P GOOD |
| `2pbd` | 2P BAD |
| `2ppr` | 2P POOR |
| `2pcb` | 2P COMBO |
| `2pfast` | 2P FAST 计数 |
| `2pslow` | 2P SLOW 计数 |
| `1pbscore` ~ `1pslow` | 1P 对应字段 |

## 启动服务

```bash
python serve.py --font font/ --port 9877 --rois-csv rois.csv --image-size 1920,1080
```

**参数说明：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--font` | `font/` | 字体模板目录 |
| `--port` | `9877` | TCP 端口 |
| `--host` | `127.0.0.1` | 绑定地址 |
| `--rois-csv` | `None` | ROI 配置文件路径 |
| `--image-size` | `1920,1080` | 期望图像尺寸（会自动缩放） |

## Python 客户端示例

```python
import socket
import struct
import json

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 9877))

# 读取图像
with open('screenshot.png', 'rb') as f:
    img_bytes = f.read()

# 发送: 4字节长度 + 图像数据
sock.sendall(struct.pack('>I', len(img_bytes)) + img_bytes)

# 接收 JSON 响应
response = sock.recv(4096).decode()
result = json.loads(response.strip())
print(result)  # {'2pbscore': '1626', '2pscore': '1234', ...}

# 关闭连接
sock.close()
```

## 测试

```bash
# 测试单张图片
python test.py data/screenshot.png 920 340 60 25

# 测试模板自匹配
python test.py --test-font
```

## 文件结构

```
iidx_score_reco/
├── recognizer.py      # 核心数字识别类 (IIDXDigitRecognizer)
├── serve.py           # TCP 推理服务
├── test.py            # 测试脚本
├── rois.csv           # ROI 区域配置文件
├── font/              # 数字模板目录 (0.png - 9.png)
└── data/              # 测试截图目录
```

## 核心识别流程

```
截图 → ROI裁剪 → 白色掩码提取 → 数字分割 → 模板匹配 → JSON结果
```

识别器使用二值化模板匹配算法，支持自动图像缩放以适应不同分辨率截图。

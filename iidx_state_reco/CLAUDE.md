# 项目：视频帧图像分类标注工具

## 快速上手

### 1. 标注数据（二选一）

**Web 工具（推荐）**：
```bash
python3 webapp.py
# 浏览器访问 http://localhost:5000
# 快捷键：1-9/a-i 选择标签，←/→ 翻页
```

**桌面工具**：
```bash
python3 annotate.py "2026-03-18 13-08-41/"
```

### 2. 训练模型

```bash
python3 train.py
# 输出：classifier.pth, classifier.labels.txt
```

### 3. 导出 ONNX（可选，加速推理）

```bash
python3 export_onnx.py --model classifier.onnx
```

### 4. 推理使用

**单次推理**：
```bash
python3 infer.py --model classifier.pth frame.jpg
```

**实时服务**（供其他程序调用）：
```bash
# 启动服务
python3 serve.py --model classifier.onnx

# Python 客户端调用
import socket, struct
with socket.socket(socket.AF_UNIX) as s:
    s.connect("/tmp/iidx_infer.sock")
    s.sendall(struct.pack(">I", len(img_bytes)) + img_bytes)
    label = s.recv(256).decode().strip()  # 如 "play"
```

---

## 目录结构

```
iidx_state_reco/
├── CLAUDE.md           # 本文件
├── tags.txt            # 标签定义（19个标签，每行一个）
├── annotate.py         # 原版 tkinter 桌面工具
├── webapp.py           # Flask Web 后端
├── train.py            # MobileNetV3-Small 分类器训练脚本
├── infer.py            # 推理脚本（支持单帧/目录/测速）
├── serve.py            # 推理服务（Unix socket/TCP）
├── templates/
│   └── index.html      # Web 前端（单页应用）
└── <session>/          # 会话目录，如 "2025-09-23 22-39-42"
    ├── frame_000001.jpg
    ├── frame_000002.jpg
    ├── ...
    └── annotations.csv # 标注结果（由工具自动生成）
```

## 数据说明

- **会话目录**：按日期时间命名（`YYYY-MM-DD HH-MM-SS`），每个对应一段视频的1fps抽帧
- **图像文件**：`frame_NNNNNN.jpg`，分辨率 240×135，每个会话数百帧（约150–774帧）
- **标签文件** `tags.txt`：**19个标签**（idle / splash / blank / entry / pay / interlude / modesel / dansel / songsel / confirm / play / death / score / danscore / lab / others / await / aconfirm / arank）
- **标注输出** `annotations.csv`：CSV 格式，两列 `filename,label`，保存在各会话目录下
- **数据规模**（截至 2026-03-21）：12个会话，共 3983 帧已标注；类分布不均，play=1067 为最多，idle=2、arank=9 极少

## Web 工具（webapp.py）

### 启动

```bash
python3 webapp.py
# 访问 http://localhost:5000
```

依赖：Flask（`pip install flask`）

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 前端页面 |
| GET | `/api/tags` | 返回标签列表 |
| GET | `/api/sessions` | 返回所有会话及进度 |
| GET | `/api/session/<name>/images` | 返回会话帧列表及已有标注 |
| GET | `/img/<session>/<filename>` | 返回图像文件 |
| POST | `/api/session/<name>/annotate` | 保存标注 `{filename: label, ...}` |

### 前端快捷键

| 快捷键 | 操作 |
|--------|------|
| `1`–`9` | 应用第 1–9 个标签并自动跳到下一帧 |
| `a`–`i` | 应用第 10–18 个标签 |
| `← / →` | 前/后一帧 |
| `Enter` | 应用输入框中的标签 |
| `Ctrl+S` | 手动保存 |

- 每次标注后自动延迟 1.5 秒保存（防抖）
- 标注格式与 `annotate.py`（tkinter 工具）完全兼容

## 原版桌面工具（annotate.py）

基于 tkinter + Pillow，依赖：`pip install pillow`

```bash
python3 annotate.py ["session dir"]
```

功能基本相同，输出同样的 `annotations.csv`。

---

## 分类器训练（train.py）

### 模型选型

**MobileNetV3-Small**（torchvision 预训练，ImageNet 权重 fine-tune）

| 指标 | 值 |
|------|----|
| 参数量 | 2.5M |
| 输入尺寸 | 224×224 |
| 目标推理速度 | GTX 1060 / Tesla P4 实时（500+ FPS） |
| 依赖 | `pip install torch torchvision` |

选型理由：图像已为 240×135 的 UI 截图，类间视觉差异显著，轻量模型精度足够；
不均衡问题（idle=2, arank=9 极稀少）通过 WeightedRandomSampler + CrossEntropyLoss(weight) 双重处理。

### 训练策略

两阶段训练：
1. **阶段 1**：冻结 backbone，只训练分类头（lr=1e-3，默认 10 epochs）
2. **阶段 2**：解冻全网络 fine-tune（backbone lr=1e-4，head lr=5e-4，默认 20 epochs）

数据划分：按会话分割（最后 1 个会话作验证集），避免时序泄漏。
实际规模：训练 ~2467 帧，验证 ~1516 帧（验证会话：`2026-03-18 13-08-41`）。

### 运行

```bash
python3 train.py
# 可选参数
python3 train.py --epochs-head 10 --epochs-full 30 --batch-size 32 --output classifier.pth
```

输出文件：
- `classifier.pth`：模型权重
- `classifier.labels.txt`：`<index>\t<label>` 映射表

---

## 推理脚本（infer.py）

```bash
# 测速
python3 infer.py --model classifier.pth --benchmark

# 对单张图像推理
python3 infer.py --model classifier.pth frame.jpg

# 对整个会话目录批量推理
python3 infer.py --model classifier.pth "2026-03-18 13-08-41/"
```

---

## 推理服务（serve.py）

长时间运行，通过 Unix socket 或 TCP 接收图片并实时返回分类结果。

### 启动服务

```bash
# Unix socket（默认: /tmp/iidx_infer.sock）
python3 serve.py --model classifier.onnx

# TCP 端口 9876
python3 serve.py --model classifier.onnx --tcp 9876
```

依赖：`pip install onnxruntime pillow`（GPU: `onnxruntime-gpu`）

### 通信协议

每次请求：
```
发送: [4字节大端长度] [JPEG/PNG 图像字节]
接收: [标签字符串\n]    例如 "play\n"
```

### Python 客户端示例

```python
import socket, struct

def infer(sock_path: str, img_path: str) -> str:
    with open(img_path, "rb") as f:
        data = f.read()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(sock_path)
        s.sendall(struct.pack(">I", len(data)) + data)
        return s.recv(256).decode().strip()

result = infer("/tmp/iidx_infer.sock", "frame.jpg")
print(result)  # 输出如 "play"
```

---

## 工具参数速查

### annotate.py
| 参数 | 说明 |
|------|------|
| `[session_dir]` | 会话目录路径，默认为当前目录 |

### webapp.py
| 参数 | 说明 |
|------|------|
| `--host` | 绑定地址，默认 0.0.0.0 |
| `--port` | 端口，默认 5000 |

### train.py
| 参数 | 说明 |
|------|------|
| `--epochs-head` | 阶段 1 epoch 数，默认 10 |
| `--epochs-full` | 阶段 2 epoch 数，默认 20 |
| `--batch-size` | 默认 32 |
| `--lr-head` | 阶段 1 学习率，默认 1e-3 |
| `--lr-full` | 阶段 2 学习率，默认 5e-4 |
| `--output` | 输出模型路径，默认 classifier.pth |

### infer.py / infer_onnx.py
| 参数 | 说明 |
|------|------|
| `--model` | 模型文件路径（.pth 或 .onnx） |
| `--labels` | 标签文件路径，默认同名 .labels.txt |
| `--top` | 显示 Top-N 预测，默认 3 |
| `--benchmark` | 性能测速模式 |
| `--no-cuda` | 强制使用 CPU（仅 infer.py） |

### serve.py
| 参数 | 说明 |
|------|------|
| `--model` | ONNX 模型路径，默认 classifier.onnx |
| `--labels` | 标签文件路径 |
| `--sock` | Unix socket 路径，默认 /tmp/iidx_infer.sock |
| `--tcp PORT` | 改用 TCP 模式，指定端口 |

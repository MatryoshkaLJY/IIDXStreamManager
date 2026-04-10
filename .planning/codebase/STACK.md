# Technology Stack

**Analysis Date:** 2026-04-10

## Languages

**Primary:**
- **Python 3.8+** - Core application logic, ML inference, and backend services
- **JavaScript (ES6+)** - Frontend for BPL scoreboard display
- **HTML/CSS** - UI templates and styling

**Secondary:**
- **YAML** - State machine configuration (`state_machine.yaml`)
- **CSV** - ROI configurations and annotation data

## Runtime & Environment

**Environment:**
- Python 3.8 or higher
- No virtual environment configuration detected (uses system Python)

**Package Manager:**
- pip (standard Python package manager)
- npm (for Node.js dependencies in `iidx_bpl_scoreboard/`)

## Core Dependencies

### Machine Learning & Computer Vision
| Package | Purpose | Location Used |
|---------|---------|---------------|
| `torch` | PyTorch framework for model training | `iidx_state_reco/train.py` |
| `torchvision` | Pre-trained MobileNetV3-Small model | `iidx_state_reco/train.py` |
| `onnxruntime` / `onnxruntime-gpu` | ONNX model inference (CPU/GPU) | `iidx_state_reco/serve.py` |
| `opencv-python` | Image processing and template matching | `iidx_score_reco/recognizer.py` |
| `Pillow (PIL)` | Image I/O and preprocessing | Multiple modules |
| `numpy` | Numerical operations and array handling | All ML modules |

### Web & Networking
| Package | Purpose | Location Used |
|---------|---------|---------------|
| `flask` | Web annotation tool backend | `iidx_state_reco/webapp.py` |
| `websockets` | WebSocket server for BPL scoreboard | `iidx_bpl_scoreboard/server.py` |
| `ws` (Node.js) | WebSocket client library | `iidx_bpl_scoreboard/package.json` |
| `streamlit` | TPL scene switcher web UI | `tpl_scene_switcher/streamlit_app.py` |

### OBS Integration
| Package | Purpose | Location Used |
|---------|---------|---------------|
| `obsws-python` | OBS WebSocket 5.x API client | `obs_manager/obs_manager.py` |
| `obs-websocket-py` | OBS WebSocket client (legacy) | `tpl_scene_switcher/switcher.py` |

### Hardware & Serial
| Package | Purpose | Location Used |
|---------|---------|---------------|
| `pyserial` | Serial port communication for hardware control | `tpl_scene_switcher/switcher.py` |

### Data & Configuration
| Package | Purpose | Location Used |
|---------|---------|---------------|
| `pyyaml` | YAML parsing for state machine config | `iidx_state_machine/state_machine.py` |

## Frameworks & Architecture Patterns

**Deep Learning Framework:**
- PyTorch with torchvision.models
- Model: MobileNetV3-Small (2.5M parameters, ImageNet pre-trained)
- Export format: ONNX for optimized inference

**Web Frameworks:**
- Flask (lightweight Python web framework)
- Streamlit (data app framework)
- Vanilla JavaScript (no frontend framework)

**Communication Patterns:**
- TCP sockets for inter-service communication
- Unix domain sockets (optional) for local inference
- WebSocket for real-time scoreboard updates
- OBS WebSocket protocol for broadcast software integration

## Project Structure by Module

### 1. iidx_state_reco (State Recognition)
- **Technology:** PyTorch, ONNX Runtime, Flask, PIL
- **Model:** MobileNetV3-Small classifier (19 classes)
- **Input:** 224x224 RGB images
- **Output:** Game state labels (idle, play, score, etc.)
- **Serving:** TCP socket server (port 9876 default) or Unix socket

### 2. iidx_score_reco (Score Recognition)
- **Technology:** OpenCV, NumPy, PIL
- **Method:** Template matching with multi-scale support
- **Input:** 1920x1080 game screenshots
- **Output:** JSON with recognized digits from ROI regions
- **Serving:** TCP socket server (port 9877 default)

### 3. iidx_state_machine (Game State Management)
- **Technology:** Python dataclasses, PyYAML
- **Pattern:** Hierarchical state machine with 33 states
- **Configuration:** YAML-based state definitions
- **Serving:** TCP server mode (port 9999) or file input mode

### 4. obs_manager (OBS Integration)
- **Technology:** obsws-python, PIL, socket
- **Function:** Multi-machine game state tracking
- **Integration:** OBS WebSocket 5.x API

### 5. iidx_bpl_scoreboard (BPL-style Scoreboard)
- **Technology:** HTML5, CSS3, vanilla JavaScript
- **Backend:** Python websockets relay server
- **Protocol:** Custom WebSocket JSON protocol
- **Fonts:** Google Fonts (Orbitron, Rajdhani)

### 6. tpl_scene_switcher (TPL Tournament Tool)
- **Technology:** Streamlit, obs-websocket-py, pyserial
- **Function:** Scene switching with serial hardware control

## Build & Deployment

**No formal build system detected.**

**Manual setup required:**
```bash
# State recognition dependencies
pip install torch torchvision onnxruntime pillow numpy

# Score recognition dependencies  
pip install opencv-python numpy pillow

# OBS manager dependencies
pip install obsws-python pillow

# State machine dependencies
pip install pyyaml

# BPL scoreboard dependencies (Python)
pip install websockets

# TPL switcher dependencies
pip install streamlit obs-websocket-py pyserial

# Web annotation tool
pip install flask
```

**Node.js dependencies (BPL scoreboard):**
```bash
cd iidx_bpl_scoreboard
npm install  # Installs ws@^8.20.0
```

## Model Artifacts

| Model | Location | Format | Size |
|-------|----------|--------|------|
| State classifier | `iidx_state_reco/classifier.pth` | PyTorch | ~6.3 MB |
| State classifier (ONNX) | `iidx_state_reco/classifier.onnx` | ONNX | ~305 KB |
| Digit templates | `iidx_score_reco/font/` | PNG images | Binary assets |

## Platform Requirements

**Development:**
- Linux/macOS/Windows with Python 3.8+
- OBS Studio 28+ with WebSocket plugin
- Optional: CUDA-capable GPU for inference acceleration

**Production/Streaming:**
- OBS Studio with WebSocket server enabled
- Network connectivity between components
- Serial port access (for TPL hardware control)

---

*Stack analysis: 2026-04-10*

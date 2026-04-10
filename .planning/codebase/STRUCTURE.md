# Codebase Structure

**Analysis Date:** 2026-04-10

## Directory Layout

```
/home/matryoshka/Downloads/out_frames/
├── README.md                          # Project documentation (trilingual)
├── .gitignore                         # Git ignore rules
│
├── iidx_state_reco/                   # Game state recognition (CNN classifier)
│   ├── serve.py                       # TCP/Unix socket inference server
│   ├── train.py                       # MobileNetV3 training script
│   ├── infer.py                       # Batch inference utility
│   ├── infer_onnx.py                  # ONNX-specific inference
│   ├── export_onnx.py                 # PyTorch to ONNX export
│   ├── annotate.py                    # Desktop annotation tool (tkinter)
│   ├── webapp.py                      # Flask web annotation tool
│   ├── tags.txt                       # Label definitions (19 classes)
│   ├── templates/
│   │   └── index.html                 # Web annotation UI
│   └── data/                          # Training datasets
│       ├── 2025-09-23 22-39-42/       # Session directories
│       ├── 2025-09-23 22-55-04/
│       ├── arena/                     # Arena mode frames
│       ├── bpl/                       # BPL tournament frames
│       ├── carena/                    # Cleaned arena data
│       └── kbpl/                      # Korean BPL data
│
├── iidx_score_reco/                   # Score recognition (template matching)
│   ├── serve.py                       # TCP inference server
│   ├── recognizer.py                  # IIDXDigitRecognizer class
│   ├── test.py                        # Test script
│   ├── font/                          # Digit templates (0-9)
│   └── data/                          # Test screenshots
│
├── iidx_state_machine/                # Game state machine
│   ├── state_machine.py               # IIDXStateMachine implementation
│   ├── state_machine.yaml             # State/transition definitions
│   ├── test_client.py                 # TCP client for testing
│   └── test_state_machine_manager.py  # Multi-machine tests
│
├── obs_manager/                       # OBS Studio integration
│   ├── obs_manager.py                 # OBSManager class (main module)
│   ├── web_monitor.py                 # Flask web monitoring UI
│   ├── monitor_config.json            # Saved configuration
│   ├── templates/                     # Flask HTML templates
│   │   └── monitor.html               # Main monitoring dashboard
│   └── test_*.py                      # Unit tests
│
├── iidx_bpl_scoreboard/               # BPL-style tournament overlay
│   ├── server.py                      # WebSocket relay server
│   ├── app.js                         # Frontend JavaScript
│   ├── index.html                     # Scoreboard display
│   ├── config.json                    # Default configuration
│   ├── PROTOCOL.md                    # WebSocket protocol docs
│   ├── package.json                   # Node.js dependencies
│   ├── testbench/
│   │   ├── testbench.py               # Python test client
│   │   ├── test_relay.py              # Relay test script
│   │   └── data.json                  # Sample match data
│   └── example/                       # Example configurations
│
├── tpl_scene_switcher/                # TPL tournament scene switcher
│   ├── streamlit_app.py               # Streamlit web interface
│   ├── switcher.py                    # OBSSceneSwitcher class
│   ├── main.py                        # CLI entry point
│   └── run_app.py                     # Alternative runner
│
├── iidx_stream_state_machine/         # Stream processing state machine
│   ├── src/                           # Source modules
│   ├── tests/                         # Test suite
│   └── tmp/                           # Temporary files
│
├── .claude/                           # Claude Code configuration
│   ├── logs/                          # Session logs
│   └── settings.local.json            # Local settings
│
└── .vscode/                           # VS Code configuration
```

## Directory Purposes

### `iidx_state_reco/`
**Purpose:** Deep learning-based game screen classification
**Contains:** Training scripts, inference servers, annotation tools
**Key Files:**
- `serve.py` - Production inference server (ONNX Runtime)
- `train.py` - MobileNetV3 training with class balancing
- `webapp.py` - Web-based annotation interface

**Data Organization:**
- Session directories named `YYYY-MM-DD HH-MM-SS`
- Each contains `frame_NNNNNN.jpg` and `annotations.csv`
- Aggregated training data in subdirectories (arena/, bpl/, etc.)

### `iidx_score_reco/`
**Purpose:** OCR for score digits using template matching
**Contains:** Recognition engine, templates, test data
**Key Files:**
- `recognizer.py` - `IIDXDigitRecognizer` class with OpenCV
- `serve.py` - TCP service wrapper
- `font/` - Binary templates for digits 0-9

### `iidx_state_machine/`
**Purpose:** Game flow state management
**Contains:** State machine engine and YAML configuration
**Key Files:**
- `state_machine.py` - Core engine with 33 states
- `state_machine.yaml` - Declarative configuration

### `obs_manager/`
**Purpose:** OBS WebSocket integration and orchestration
**Contains:** OBS client, web monitoring UI
**Key Files:**
- `obs_manager.py` - Main `OBSManager` class (640 lines)
- `web_monitor.py` - Flask app with REST API
- `templates/monitor.html` - Dashboard UI

### `iidx_bpl_scoreboard/`
**Purpose:** Professional tournament scoreboard overlay
**Contains:** WebSocket server, frontend, test tools
**Key Files:**
- `server.py` - Python WebSocket relay
- `app.js` - Frontend scoreboard logic
- `index.html` - Display layout

### `tpl_scene_switcher/`
**Purpose:** Manual tournament scene control
**Contains:** Streamlit UI, OBS scene controller
**Key Files:**
- `streamlit_app.py` - Web UI for scene switching
- `switcher.py` - `OBSSceneSwitcher` class with serial control

## Key File Locations

### Entry Points
| File | Purpose | Usage |
|------|---------|-------|
| `iidx_state_reco/serve.py` | State inference server | `python serve.py --model model.onnx --tcp 9876` |
| `iidx_score_reco/serve.py` | Score inference server | `python serve.py --font font/ --port 9877` |
| `obs_manager/obs_manager.py` | OBS CLI tool | `python obs_manager.py --host localhost --port 4455` |
| `obs_manager/web_monitor.py` | Web monitoring | `python web_monitor.py --port 5001` |
| `iidx_state_machine/state_machine.py` | State machine server | `python state_machine.py --mode tcp` |
| `iidx_bpl_scoreboard/server.py` | Scoreboard relay | `python server.py` (port 8080) |
| `tpl_scene_switcher/streamlit_app.py` | Scene switcher UI | `streamlit run streamlit_app.py` |

### Configuration Files
| File | Purpose | Format |
|------|---------|--------|
| `iidx_state_machine/state_machine.yaml` | State definitions | YAML |
| `obs_manager/monitor_config.json` | Monitor settings | JSON |
| `iidx_bpl_scoreboard/config.json` | Scoreboard defaults | JSON |
| `iidx_score_reco/rois.csv` | Score ROI coordinates | CSV |
| `iidx_state_reco/tags.txt` | Classification labels | Text |

### Core Classes
| File | Class | Responsibility |
|------|-------|----------------|
| `obs_manager/obs_manager.py` | `OBSManager` | OBS WebSocket client |
| `obs_manager/obs_manager.py` | `MachineConfig` | Per-machine configuration |
| `iidx_state_machine/state_machine.py` | `IIDXStateMachine` | Single machine state tracking |
| `iidx_state_machine/state_machine.py` | `IIDXStateMachineManager` | Multi-machine manager |
| `iidx_score_reco/recognizer.py` | `IIDXDigitRecognizer` | OCR engine |
| `tpl_scene_switcher/switcher.py` | `OBSSceneSwitcher` | Scene control |

## Naming Conventions

### Files
- **Scripts:** `snake_case.py` (e.g., `state_machine.py`)
- **Classes:** `PascalCase` matching filename (e.g., `IIDXStateMachine` in `state_machine.py`)
- **Tests:** `test_*.py` or `*_test.py`
- **Configs:** `*.yaml`, `*.json`, `*.csv` as appropriate

### Directories
- **Module directories:** `snake_case` with `iidx_` prefix
- **Data directories:** Date-time format `YYYY-MM-DD HH-MM-SS`
- **Subdirectories:** Descriptive lowercase (e.g., `templates/`, `testbench/`)

### Variables (Python)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `DEFAULT_ROIS`, `MEAN`, `STD`)
- **Functions/Methods:** `snake_case` (e.g., `capture_source`, `process_event`)
- **Private:** `_leading_underscore` (e.g., `_setup_logging`, `_load_config`)
- **Class Attributes:** `snake_case` in dataclasses

## Where to Add New Code

### New Recognition Model
1. **Implementation:** Add to `iidx_state_reco/`
2. **Training:** Extend `train.py` or create `train_newmodel.py`
3. **Inference:** Add to `serve.py` or create new `serve_*.py`
4. **Tests:** Add to `iidx_state_reco/tests/` (create if needed)

### New Game Mode Support
1. **States:** Add to `iidx_state_machine/state_machine.yaml`
- Add state definitions in `states:` section
- Add transitions in `transitions:` section
- Add any new actions in `actions:` section

2. **Variables:** Add to `variables:` section if tracking new counters

3. **Action Handlers:** Add to `state_machine.py`:
```python
def _new_action(self) -> None:
    """Description of action."""
    self.variables['new_var'] = value

# Register in _get_action_handler()
action_map = {
    'new_action': self._new_action,
    # ...
}
```

### New OBS Integration Feature
1. **Core Logic:** Add method to `OBSManager` class in `obs_manager/obs_manager.py`
2. **Web UI:** Add endpoint to `web_monitor.py` and template to `templates/`
3. **API:** Follow existing REST pattern:
```python
@app.route("/api/new_feature", methods=["POST"])
def new_feature():
    # Implementation
    return jsonify({"ok": True})
```

### New Overlay/Display
1. **Create directory:** `new_overlay/`
2. **Follow BPL pattern:**
   - `server.py` - WebSocket/HTTP server
   - `index.html` - Display layout
   - `app.js` - Frontend logic
   - `config.json` - Default settings

## Special Directories

### `iidx_state_reco/data/`
**Purpose:** Training datasets
**Structure:**
```
data/
├── YYYY-MM-DD HH-MM-SS/      # Session directories
│   ├── frame_000001.jpg
│   ├── frame_000002.jpg
│   └── annotations.csv       # filename,label pairs
├── arena/                     # Aggregated arena data
├── bpl/                       # BPL tournament data
└── kbpl_cleaned/              # Cleaned Korean BPL data
```

**Generated:** Yes (from video capture)
**Committed:** No (in .gitignore)

### `iidx_score_reco/font/`
**Purpose:** Digit templates for OCR
**Contents:** `0.png` through `9.png` (binary images)
**Size:** 20x30 pixels per template

### `.claude/logs/`
**Purpose:** Claude Code session history
**Generated:** Yes (auto-created)
**Committed:** No

### `__pycache__/`
**Purpose:** Python bytecode cache
**Generated:** Yes
**Committed:** No (in .gitignore)

## Import Patterns

### Within Project
```python
# From obs_manager to state_machine
sys.path.insert(0, parent_dir)
from iidx_state_machine.state_machine import IIDXStateMachineManager

# Relative imports within module
from recognizer import IIDXDigitRecognizer
```

### External Dependencies
```python
# Deep learning
torch, torchvision, onnxruntime

# Computer vision
opencv-python (cv2), Pillow (PIL)

# Web
flask, flask_cors, streamlit, websockets

# Data
numpy, pyyaml

# OBS
obsws-python, obswebsocket
```

## Build/Deployment Artifacts

### Model Files
- `*.pth` - PyTorch weights (not committed)
- `*.onnx` - ONNX models (not committed)
- `*.labels.txt` - Label mappings (committed)

### Configuration
- `monitor_config.json` - User-specific (not committed)
- `state_machine.yaml` - Shared (committed)

### Node.js
- `node_modules/` - Dependencies (not committed)
- `package-lock.json` - Lock file (committed)

---

*Structure analysis: 2026-04-10*

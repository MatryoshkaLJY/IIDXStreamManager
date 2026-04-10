# Architecture

**Analysis Date:** 2026-04-10

## Overview

IIDX Stream Manager is a comprehensive toolset for beatmania IIDX arcade game streaming. It provides automated scene recognition, score tracking, state management, and professional broadcasting overlays.

**Overall Pattern:** Modular microservices architecture with clear separation of concerns between computer vision inference, state management, and OBS integration.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OBS Studio (Video Source)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OBS Manager (WebSocket)                            │
│                      `obs_manager/obs_manager.py`                            │
│  - Connects to OBS WebSocket API                                             │
│  - Captures video frames from sources                                        │
│  - Routes frames to inference services                                       │
│  - Manages multi-machine state tracking                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐
│   State Recognition │  │   Score Recognition │  │    State Machine        │
│   (TCP/Unix Socket) │  │   (TCP)             │  │    (YAML Configured)    │
│   Port: 9876        │  │   Port: 9877        │  │                         │
│                     │  │                     │  │                         │
│ `iidx_state_reco/`  │  │ `iidx_score_reco/`  │  │ `iidx_state_machine/`   │
│ - serve.py          │  │ - serve.py          │  │ - state_machine.py      │
│ - train.py          │  │ - recognizer.py     │  │ - state_machine.yaml    │
│ - MobileNetV3       │  │ - Template matching │  │ - 33 states, 27 events  │
└─────────────────────┘  └─────────────────────┘  └─────────────────────────┘
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Web Monitor (Flask)                                  │
│                      `obs_manager/web_monitor.py`                            │
│  - Web UI for configuration                                                  │
│  - Real-time monitoring dashboard                                            │
│  - Score history tracking                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐
│   BPL Scoreboard    │  │   TPL Scene Switcher│  │   External Displays     │
│   (WebSocket)       │  │   (Streamlit)       │  │                         │
│                     │  │                     │  │                         │
│ `iidx_bpl_scoreboard│  │ `tpl_scene_switcher`│  │ - Browser overlays      │
│ - server.py (relay) │  │ - streamlit_app.py  │  │ - Serial devices        │
│ - app.js (frontend) │  │ - switcher.py       │  │ - Tournament systems    │
│ - index.html        │  │ - OBS scene ctrl    │  │                         │
└─────────────────────┘  └─────────────────────┘  └─────────────────────────┘
```

## Layers

### 1. Video Capture Layer
**Purpose:** Capture video frames from OBS Studio
**Location:** `obs_manager/obs_manager.py`
**Key Components:**
- `OBSManager` class - WebSocket client for OBS
- `capture_source()` - Frame extraction with resizing
- `capture_and_recognize()` - Frame capture + inference

**Depends on:** OBS Studio WebSocket plugin
**Used by:** State recognition, score recognition

### 2. Computer Vision Layer
**Purpose:** Deep learning inference for game state and score recognition

#### 2a. State Recognition (`iidx_state_reco/`)
- **Model:** MobileNetV3-Small CNN classifier
- **Input:** 224x224 RGB frames
- **Output:** 19 class labels (idle, play, score, etc.)
- **Inference:** ONNX Runtime (CPU/GPU)
- **Protocol:** TCP/Unix socket with 4-byte length prefix

#### 2b. Score Recognition (`iidx_score_reco/`)
- **Method:** Template matching with OpenCV
- **Input:** 1920x1080 score screen
- **Output:** JSON with validated scores (1P/2P)
- **Validation:** Score = 2*PG + GR formula check
- **Protocol:** TCP socket

### 3. State Management Layer
**Purpose:** Track game flow and mode transitions
**Location:** `iidx_state_machine/state_machine.py`
**Key Components:**
- `IIDXStateMachine` - Single machine state tracker
- `IIDXStateMachineManager` - Multi-machine manager
- YAML-defined states, transitions, actions, variables

**States (33 total):**
- Core: IDLE, ENTRY, MODESEL, LOGOUT
- Arena: A_WAIT, A_SONGSEL, A_PLAY, A_SCORE, etc.
- Battle: B_WAIT, B_MODESEL, B_PLAY, B_SCORE, etc.
- Standard: S_SONGSEL, S_PLAY, S_SCORE, S_DEATH, etc.
- Dan: D_SEL, D_PLAY, D_SCORE_S, D_SCORE_D, etc.

**Variables:**
- `arena_round`, `battle_round` - Round counters
- `std_song_count`, `std_retry_count` - Standard mode tracking
- `dan_song_count` - Dan mode progress
- `play_type` - 1P/2P/Versus/Double play
- `blank_counter` - Safety reset mechanism

### 4. Integration Layer
**Purpose:** Combine CV results with state management
**Location:** `obs_manager/obs_manager.py` (methods: `init_state_machine`, `process_frame`)

**Flow:**
1. Capture frame from OBS source
2. Send to state recognition service
3. Feed label to state machine
4. If SCORE state triggered, capture score
5. Validate and store results

### 5. Presentation Layer
**Purpose:** Display and control interfaces

#### 5a. Web Monitor (`obs_manager/web_monitor.py`)
- Flask-based web UI
- Real-time machine status
- Score history with validation
- Configuration management

#### 5b. BPL Scoreboard (`iidx_bpl_scoreboard/`)
- Professional tournament overlay
- WebSocket-based real-time updates
- Team/player/score display

#### 5c. TPL Scene Switcher (`tpl_scene_switcher/`)
- Streamlit-based control interface
- OBS scene switching
- Serial device control for hardware

## Data Flow

### Main Recognition Flow
```
OBS Source → OBSManager.capture_source() → State Recognition Service
                                                  ↓
State Machine.process_event(label) ←──┬── State label
                                      │
    ┌─────────────────────────────────┘
    ▼
If state has "get_score" action:
    OBSManager.capture_and_recognize_score() → Score Recognition Service
                                                      ↓
                                            JSON scores + validation
```

### Score Validation Flow
```
Score Image → ROI Extraction → Digit Segmentation → Template Matching
                                                          ↓
                                            Raw digit strings
                                                          ↓
                                            Formula Validation
                                                (score = 2*PG + GR)
                                                          ↓
                                            {1pscore, 1ppg, 1pgr, 1p_valid, ...}
```

### State Machine Event Processing
```
Input Event → Find Transition → Check Guards → Execute Actions
                                                  ↓
                                        Update Variables
                                                  ↓
                                        Change State (if applicable)
                                                  ↓
                                        Return JSON Result
```

## Key Abstractions

### MachineConfig
**Purpose:** Configuration for a single game cabinet
**Location:** `obs_manager/obs_manager.py` (line 55)
```python
@dataclass
class MachineConfig:
    machine_id: str
    source_name: str
    state_infer_addr: Union[str, Tuple[str, int]]
    score_infer_addr: Tuple[str, int]
    pending_score_validation: bool
    last_invalid_scores: Optional[dict]
```

### State/Transition/Variable Dataclasses
**Purpose:** YAML configuration representation
**Location:** `iidx_state_machine/state_machine.py` (lines 19-44)
```python
@dataclass
class State:
    id: str
    description: str
    is_initial: bool

@dataclass
class Transition:
    from_state: str
    to_state: Optional[str]
    events: List[str]
    guards: List[Dict[str, Any]]
    actions: List[str]
```

## Entry Points

### 1. State Recognition Server
**File:** `iidx_state_reco/serve.py`
**Purpose:** TCP/Unix socket inference service
**Command:** `python serve.py --model classifier.onnx --tcp 9876`

### 2. Score Recognition Server
**File:** `iidx_score_reco/serve.py`
**Purpose:** Score digit recognition service
**Command:** `python serve.py --font font/ --port 9877`

### 3. OBS Manager (CLI)
**File:** `obs_manager/obs_manager.py`
**Purpose:** Single-shot capture and recognition
**Command:** `python obs_manager.py --host localhost --port 4455 --password xxx`

### 4. Web Monitor
**File:** `obs_manager/web_monitor.py`
**Purpose:** Full web-based monitoring system
**Command:** `python web_monitor.py --port 5001`
**URL:** http://localhost:5001

### 5. State Machine (Standalone)
**File:** `iidx_state_machine/state_machine.py`
**Purpose:** Debug/test state machine
**Command:** `python state_machine.py --config state_machine.yaml --mode tcp`

### 6. BPL Scoreboard Server
**File:** `iidx_bpl_scoreboard/server.py`
**Purpose:** WebSocket relay for scoreboard
**Command:** `python server.py` (port 8080)

### 7. TPL Scene Switcher
**File:** `tpl_scene_switcher/streamlit_app.py`
**Purpose:** Tournament scene control UI
**Command:** `streamlit run streamlit_app.py`

## Design Patterns

### 1. Microservices
Each major function runs as independent service with defined protocols:
- State recognition: TCP/Unix socket with length-prefixed binary
- Score recognition: TCP with JSON responses
- State machine: TCP with line-delimited JSON

### 2. State Machine Pattern
Declarative state transitions via YAML:
- States define game phases
- Transitions define valid flows
- Guards control conditional transitions
- Actions execute side effects

### 3. Factory Pattern
Model loading in training:
- `build_model()` creates MobileNetV3 with custom head
- `freeze_backbone()` / `unfreeze_all()` control training scope

### 4. Template Method
Score recognition pipeline:
- `_extract_digit_mask()` - preprocessing
- `_segment_digits()` - character separation
- `_match_template()` - digit classification

### 5. Observer Pattern
WebSocket-based updates in BPL scoreboard:
- Server broadcasts to all connected clients
- Frontend reacts to command messages

## Error Handling

### Strategy: Graceful degradation with validation

**Score Recognition:**
- Validation against game formula (score = 2*PG + GR)
- Retry mechanism for invalid scores
- Pending validation state tracking

**State Machine:**
- Blank counter safety reset (5 consecutive blanks → IDLE)
- Guard conditions prevent invalid transitions
- Unknown events logged but don't crash

**OBS Connection:**
- Connection pooling with timeout
- Automatic reconnection in web monitor
- Context manager for safe cleanup

## Cross-Cutting Concerns

### Logging
- Structured JSON logging in state machine
- Flask request logging in web monitor
- Console output with severity levels

### Configuration
- YAML-based state machine definition
- JSON-based monitor configuration
- CSV-based ROI definitions for score recognition

### Threading
- Thread-per-client in TCP servers
- Background monitoring thread in web monitor
- Thread-safe state access with locks

---

*Architecture analysis: 2026-04-10*

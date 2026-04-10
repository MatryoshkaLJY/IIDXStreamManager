# External Integrations

**Analysis Date:** 2026-04-10

## Overview

This project integrates with external broadcast software, hardware devices, and web services to create a comprehensive beatmania IIDX streaming solution.

## OBS Studio Integration

**Primary Integration Point:** `obs_manager/obs_manager.py`

**Protocol:** OBS WebSocket 5.x (via `obsws-python`)

**Connection Configuration:**
- Default host: `localhost`
- Default port: `4455`
- Authentication: Password-based (optional)

**Capabilities:**
- Capture video source screenshots (`get_source_screenshot`)
- Switch scenes (`SetCurrentProgramScene`)
- Control source visibility within groups
- Update text source content (`SetInputSettings`)

**Used By:**
- `obs_manager/obs_manager.py` - Main OBS integration module
- `tpl_scene_switcher/switcher.py` - Scene switching with serial control

**Configuration Example:**
```python
from obs_manager import OBSManager

obs = OBSManager(host="localhost", port=4455, password="your_password")
obs.connect()
```

## WebSocket Services

### 1. BPL Scoreboard WebSocket

**Location:** `iidx_bpl_scoreboard/server.py`

**Purpose:** Relay server for scoreboard control messages

**Protocol:** WebSocket (Python `websockets` library)

**Configuration:**
- Bind address: `localhost:8080`
- Message format: JSON

**Command Protocol:**
```json
// Initialize match
{"cmd": "init", "data": {"stageName": "...", "leftTeam": {...}, "rightTeam": {...}}}

// Update score
{"cmd": "score", "data": {"round": 1, "leftScore": 2, "rightScore": 0}}

// Reset
{"cmd": "reset"}
```

**Client:** `iidx_bpl_scoreboard/app.js` (browser-based display)

### 2. State Machine TCP Server

**Location:** `iidx_state_machine/state_machine.py`

**Purpose:** Game state tracking service

**Protocol:** TCP socket (line-based JSON)

**Configuration:**
- Default bind: `0.0.0.0:9999`
- Input: Event strings or JSON `{"event": "..."}`
- Output: JSON state transition results

## Inference Services (Internal TCP)

### State Recognition Service

**Location:** `iidx_state_reco/serve.py`

**Protocol:** Custom binary TCP protocol

**Configuration:**
- Default TCP: `127.0.0.1:9876`
- Alternative: Unix socket `/tmp/iidx_infer.sock`

**Request Format:**
```
[4 bytes: big-endian image length] [JPEG/PNG image data]
```

**Response Format:**
```
[label string]\n  (e.g., "play\n", "score\n")
```

### Score Recognition Service

**Location:** `iidx_score_reco/serve.py`

**Protocol:** Custom binary TCP protocol

**Configuration:**
- Default TCP: `127.0.0.1:9877`

**Request Format:**
```
[4 bytes: big-endian image length] [PNG image data (1920x1080)]
```

**Response Format:**
```json
{"1pscore": "1234", "1ppg": "600", "1pgr": "34", "1p_valid": true, "1p_expected": "1234"}
```

**Score Validation:**
- Validates: `score = 2 * pg + gr`
- Returns validation status for both 1P and 2P

## Hardware Integration

### Serial Port Control

**Location:** `tpl_scene_switcher/switcher.py`

**Purpose:** Hardware device control via serial communication

**Library:** `pyserial`

**Configuration:**
- Default port: `COM5` (Windows) or `/dev/ttyUSB0` (Linux)
- Baud rate: `115200`

**Protocol:**
- Sends single ASCII digits (0-9) to serial port
- Used for cabinet selection indicator hardware

**Usage:**
```python
from tpl_scene_switcher.switcher import OBSSceneSwitcher

switcher = OBSSceneSwitcher(com="COM5", baud=115200)
switcher.write_digit_to_serial(3)  # Sends "3" to serial
```

## External Web Services

### Google Fonts

**Location:** `iidx_bpl_scoreboard/index.html`

**Purpose:** Typography for BPL scoreboard display

**URL:** `https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@400;600;700&display=swap`

**Fonts Used:**
- Orbitron (400, 700, 900) - Sci-fi display font for numbers
- Rajdhani (400, 600, 700) - Technical font for labels

**Note:** Requires internet connectivity during scoreboard display.

## Data Flow Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  OBS Studio │────▶│ OBS Manager │────▶│  State Reco │
│  (Source)   │     │ (WebSocket) │     │   (TCP)     │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌──────────┐  ┌───────────┐
        │State    │  │  Score   │  │   BPL     │
        │Machine  │  │  Reco    │  │ Scoreboard│
        └─────────┘  └──────────┘  └───────────┘
```

## Inter-Service Communication Matrix

| Source | Target | Protocol | Port/Path | Purpose |
|--------|--------|----------|-----------|---------|
| OBS Manager | OBS Studio | WebSocket | 4455 | Screenshot capture, scene control |
| OBS Manager | State Reco | TCP | 9876 | Game state inference |
| OBS Manager | Score Reco | TCP | 9877 | Score digit recognition |
| State Machine | Clients | TCP | 9999 | State tracking service |
| BPL Server | Browser | WebSocket | 8080 | Scoreboard updates |
| TPL Switcher | OBS Studio | WebSocket | 4455 | Scene switching |
| TPL Switcher | Hardware | Serial | COM5 | Cabinet indicators |

## Configuration Files

### ROI Configuration

**Location:** `iidx_score_reco/rois.csv`

**Format:** `name,x1,y1,x2,y2`

**Purpose:** Defines regions of interest for score digit recognition

**Example:**
```csv
1pscore,1547,488,1700,517
1ppg,1547,549,1700,581
2pscore,1400,488,1547,517
2pgr,1400,549,1547,581
```

### State Machine Configuration

**Location:** `iidx_state_machine/state_machine.yaml`

**Purpose:** Defines game states, transitions, variables, and actions

**Contains:**
- 33 state definitions
- 27 event types
- 25 action types
- Variable tracking configuration

### Label Mapping

**Location:** `iidx_state_reco/tags.txt`

**Purpose:** Maps class indices to state labels

**Contains:** 27 labels (idle, splash, blank, entry, pay, interlude, modesel, dansel, songsel, confirm, play1, play2, play12, playd, bwait, bsel, brank, death, score, danscore, lab, others, await, aconfirm, arank, asum, set)

## Environment Requirements

**Network:**
- Localhost TCP ports: 4455, 9876, 9877, 9999, 8080
- Internet access (for Google Fonts, optional)

**Hardware:**
- Serial port access (for TPL hardware control)
- OBS Studio running with WebSocket plugin enabled

**File System:**
- `/tmp/iidx_infer.sock` (Unix socket, optional)
- Model files: `classifier.onnx`, `classifier.pth`
- Font templates: `font/*.png`

## Security Considerations

**No authentication on internal services:**
- Inference services (ports 9876, 9877) bind to localhost only
- State machine TCP server (port 9999) binds to 0.0.0.0 (all interfaces)
- BPL WebSocket server (port 8080) binds to localhost only

**OBS WebSocket:**
- Password authentication supported
- Credentials passed via command line or constructor

---

*Integration audit: 2026-04-10*

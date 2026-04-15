# Architecture Patterns: IIDX Tournament Auto-Director Core

**Domain:** Local web-based OBS director for arcade tournament streaming  
**Researched:** 2026-04-15  
**Confidence:** HIGH

---

## Recommended Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Operator UI (Browser)                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Mode Select  │  │ Round Prep   │  │ Cabinet Grid │  │ Score Review │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │             │
│         └─────────────────┴─────────────────┴─────────────────┘             │
│                                   ↑↓ SocketIO                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                      Flask App (port 5002, threaded)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ HTTP Routes │  │ SocketIO    │  │ Runtime     │  │ Background Worker   │ │
│  │ (Jinja2)    │  │ Handlers    │  │ State       │  │ (cabinet polling)   │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                │                    │            │
├─────────┴────────────────┴────────────────┴────────────────────┴────────────┤
│                         Integration & Control Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐   │
│  │ OBSManager      │  │ Scoreboard      │  │ Scene Controller            │   │
│  │ (obs_manager.py)│  │ WebSocket Client│  │ (transitions + source ctrl) │   │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘   │
│           │                    │                          │                  │
├───────────┴────────────────────┴──────────────────────────┴──────────────────┤
│                         External Services (existing)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ OBS Studio   │  │ State Reco   │  │ Score Reco   │  │ State Machine    │ │
│  │ WebSocket v5 │  │ TCP :9876    │  │ TCP :9877    │  │ (iidx_state_mach)│ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │
│  ┌──────────────┐  ┌──────────────┐                                          │
│  │ BPL Board    │  │ Knockout     │                                          │
│  │ WS :8080     │  │ WS :8081     │                                          │
│  └──────────────┘  └──────────────┘                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `HTTP Routes` | Serve Jinja2 pages (status, mode select, round prep, score review) | Runtime State, Config Loader |
| `SocketIO Handlers` | Push real-time cabinet states, scores, scene changes to UI; receive operator commands | Background Worker, Scene Controller, Scoreboard Client |
| `Runtime State` | Persist current tournament mode, round assignments, config paths, and review queue | HTTP Routes, SocketIO, Background Worker |
| `Background Worker` | Poll 4 cabinets via `OBSManager` on a timer; feed frames to state machine and score OCR | OBSManager, SocketIO (broadcast results) |
| `OBSManager` | Capture source screenshots, send to TCP inference services, track per-machine config | Background Worker, Scene Controller |
| `Scene Controller` | Switch OBS scenes, toggle group visibility, update text sources for gameplay overlays | SocketIO handlers (operator override), Background Worker (auto transitions) |
| `Scoreboard Client` | Forward confirmed scores to BPL (:8080) or knockout (:8081) WebSocket relays | SocketIO handlers (on operator confirm) |

---

## Recommended Project Structure

```
src/
├── app.py                 # Flask factory + SocketIO initialization
├── state.py               # RuntimeState dataclass + persistence
├── config/
│   ├── __init__.py
│   ├── loader.py          # JSON load/validate + template generation
│   └── models.py          # Pydantic schemas
├── obs/
│   ├── __init__.py
│   ├── client.py          # Thin wrapper around obsws-python (connect, scene switch, source text)
│   └── scene_controller.py# Higher-level: transition sequences, group visibility, delays
├── cabinets/
│   ├── __init__.py
│   ├── worker.py          # Background thread: poll 4 machines, emit SocketIO events
│   └── mapper.py          # Round-to-cabinet assignment logic
├── scoreboard/
│   ├── __init__.py
│   └── client.py          # Async websockets client for :8080 / :8081
├── templates/
│   ├── base.html
│   ├── status.html
│   ├── mode_select.html
│   ├── round_prep.html
│   └── score_review.html
└── static/
    ├── css/
    │   └── main.css
    └── js/
        └── operator.js    # SocketIO client for real-time updates
```

### Structure Rationale

- **`obs/`:** Isolates OBS-specific protocol details from application logic. `scene_controller.py` owns the transition state machine (Live -> Gameplay -> Scoreboard_game -> Scoreboard_web -> Live).
- **`cabinets/`:** Owns the frame-polling loop and per-round cabinet mapping. Keeps `app.py` free of threading details.
- **`scoreboard/`:** Wraps the two external WebSocket relays so the rest of the app sends a single `push_score()` call without caring about port differences.
- **`templates/` + `static/js/`:** Server-rendered HTML keeps initial load simple; `operator.js` handles SocketIO reconnection and DOM updates for cabinet grids/score cards.

---

## Patterns to Follow

### Pattern 1: Background Worker Thread with SocketIO Broadcast
**What:** A daemon thread runs the `OBSManager` polling loop and emits SocketIO events from a thread-safe wrapper.
**When:** You need continuous frame capture without blocking Flask's request handlers.
**Trade-offs:** Adds thread-safety concerns, but Flask-SocketIO handles cross-thread emission via `socketio.emit(..., namespace='/', broadcast=True)` when using an external message queue or the built-in in-memory queue with threading/async modes.

**Example:**
```python
# src/cabinets/worker.py
import threading
import time
from flask_socketio import SocketIO

class CabinetWorker:
    def __init__(self, socketio: SocketIO, obs_manager, interval: float = 1.0):
        self.socketio = socketio
        self.obs_manager = obs_manager
        self.interval = interval
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        while not self._stop.is_set():
            for machine_id in self.obs_manager.machines:
                result = self.obs_manager.process_frame(machine_id)
                self.socketio.emit("cabinet_update", result)
            self._stop.wait(self.interval)
```

### Pattern 2: Scene Controller as a State Machine
**What:** Encapsulate OBS scene transitions in a small state machine with configurable delays.
**When:** Transitions have fixed sequences (Live ↔ Gameplay ↔ Scoreboard) and operator overrides.
**Trade-offs:** Prevents scattered `set_current_program_scene` calls across handlers; makes delay logic testable.

**Example:**
```python
# src/obs/scene_controller.py
from enum import Enum, auto

class SceneState(Enum):
    LIVE = auto()
    GAMEPLAY = auto()
    SCOREBOARD_GAME = auto()
    SCOREBOARD_WEB = auto()

class SceneController:
    def __init__(self, obs_client):
        self.obs = obs_client
        self.state = SceneState.LIVE
        self.delays = {"scoreboard_game": 0, "scoreboard_web": 5, "return_live": 15}

    def to_gameplay(self, mode: str):
        scene = {"team": "SP团队赛", "dp_team": "DP团队赛", "individual": "个人赛"}.get(mode)
        self.obs.set_scene(scene)
        self.state = SceneState.GAMEPLAY

    def to_scoreboard_game(self):
        self.obs.set_scene("Scoreboard_game")
        self.state = SceneState.SCOREBOARD_GAME

    def confirm_and_to_web(self):
        # called after operator confirms score
        self.obs.set_scene("Scoreboard_web")
        self.state = SceneState.SCOREBOARD_WEB
```

### Pattern 3: Score Review Queue
**What:** A small in-memory queue holds AI-recognized scores until the operator confirms or edits them.
**When:** You need a human-in-the-loop gate before pushing to public scoreboards.
**Trade-offs:** In-memory is fine for a single-operator local app; no database needed. Persist to `RuntimeState` if you want recovery across restarts.

**Example:**
```python
# src/state.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class ScoreReviewItem:
    machine_id: str
    raw_scores: dict
    edited_scores: Optional[dict] = None
    confirmed: bool = False

@dataclass
class RuntimeState:
    config_paths: Dict[str, str] = field(default_factory=dict)
    loaded_at: Optional[str] = None
    mode: Optional[str] = None           # "team" | "individual"
    round_assignments: Dict[str, str] = field(default_factory=dict)  # player_id -> machine_id
    review_queue: List[ScoreReviewItem] = field(default_factory=list)
```

---

## Data Flow

### 1. Round Preparation Flow
```
Operator selects mode + loads config
         ↓
HTTP POST /setup_round
         ↓
Update RuntimeState (mode, assignments)
         ↓
SceneController.to_gameplay(mode)
         ↓
SocketIO emit "round_ready" -> UI shows cabinet mapping
```

### 2. Cabinet Monitoring Flow
```
Background Worker (1s interval)
         ↓
OBSManager.capture_and_recognize() per machine
         ↓
State machine processes label -> may trigger "get_score"
         ↓
OBSManager.capture_and_recognize_score() on score state
         ↓
SocketIO emit "cabinet_update" -> UI updates per-cabinet card
         ↓
If scores detected and valid -> append to RuntimeState.review_queue
         ↓
SocketIO emit "score_pending" -> UI highlights review panel
```

### 3. Score Review & Confirm Flow
```
Operator edits/confirms score in UI
         ↓
SocketIO event "confirm_score" with edited payload
         ↓
Update RuntimeState.review_queue item as confirmed
         ↓
SceneController.to_scoreboard_web() (Transition 3)
         ↓
delay(delays["scoreboard_web"])
         ↓
ScoreboardClient.push_score(mode, payload)
         ↓
delay(delays["return_live"])
         ↓
SceneController.to_live()
         ↓
SocketIO emit "score_published" -> UI returns to standby
```

### 4. Auto-Transition Flow (Transitions 1, 2, 4)
```
State machine reports state change (e.g., "play")
         ↓
Background Worker detects transition condition
         ↓
SceneController.to_gameplay() or to_scoreboard_game() or to_live()
         ↓
SocketIO emit "scene_changed" -> UI shows current scene
```

---

## Scalability Considerations

| Scale | Adjustment |
|-------|------------|
| 1 operator, 4 cabinets, local LAN | Current architecture is ideal. Threaded Flask + 1 background thread is sufficient. |
| Multiple operators | Would need session/auth separation and a proper message broker (Redis) for SocketIO. Not required. |
| Remote OBS / cloud inference | Would need async HTTP bridges and retry logic. Out of scope. |

### What Breaks First

1. **Frame capture latency** — `get_source_screenshot` over OBS WebSocket can be slow. Mitigation: lower screenshot quality/resize, or run inference services on the same machine.
2. **SocketIO message backlog** — If the operator UI disconnects/reconnects rapidly, queued events may flood the client. Mitigation: emit only diffs, not full frames.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Calling OBS WebSocket from HTTP Request Threads
**What:** Synchronous OBS calls inside Flask route handlers.
**Why bad:** `get_source_screenshot` can take 200-500ms; this blocks the Werkzeug worker and stalls the UI.
**Instead:** Route all OBS interactions through the background worker or a dedicated thread pool.

### Anti-Pattern 2: Leaking Scoreboard Protocols into Route Handlers
**What:** Hardcoding BPL/knockout message shapes inside `app.py`.
**Why bad:** The two scoreboards have different command schemas (`cmd: score` vs `cmd: settle`). Mixing them creates fragile, untestable code.
**Instead:** Encapsulate protocol translation in `scoreboard/client.py` with a mode-aware `push_score()` method.

### Anti-Pattern 3: Storing OBS Connection State in Global Variables
**What:** `obs_client = None` at module level, mutated by routes.
**Why bad:** Race conditions across threads; hard to test; unclear lifecycle.
**Instead:** Attach the `OBSManager` and `SceneController` to the Flask app context or a small registry object passed to handlers.

### Anti-Pattern 4: Polling Cabinets from the Main Thread
**What:** Running `while True: process_frame()` directly in `app.py` before `socketio.run()`.
**Why bad:** Blocks Flask-SocketIO's event loop and prevents the server from starting.
**Instead:** Start the background worker after `socketio.run()` begins, or use Flask's `before_first_request` / `@socketio.on('connect')` trigger with a singleton guard.

---

## Integration Points

### External Services

| Service | Pattern | Notes |
|---------|---------|-------|
| OBS Studio (WebSocket v5) | Synchronous `obsws.ReqClient` wrapped in `obs/client.py` | Keep connection alive; reconnect on `ConnectionError`. Scene names are Chinese strings configured in OBS. |
| State Reco (TCP :9876) | Called inside `obs_manager.py` via `socket.sendall` | Already wrapped; no changes needed. |
| Score Reco (TCP :9877) | Called inside `obs_manager.py` via `socket.sendall` | Returns JSON with `1p_valid` / `2p_valid` flags. |
| State Machine | Imported lazily by `obs_manager.py`; `process_event()` drives transitions | Must be initialized with a YAML config path. |
| BPL Scoreboard (WS :8080) | `websockets` async client | Simple broadcast relay; connect, send JSON, disconnect (or keep open). |
| Knockout Scoreboard (WS :8081) | `websockets` async client | Same relay pattern; command schema differs slightly. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `HTTP Routes ↔ Runtime State` | Direct function calls | Small, synchronous reads/writes. |
| `Background Worker ↔ SocketIO` | `socketio.emit()` | Use `socketio.emit(..., namespace='/')` from the worker thread. |
| `SocketIO Handlers ↔ Scene Controller` | Direct method calls | Scene switches are fast enough to run in the SocketIO handler thread. |
| `SocketIO Handlers ↔ Scoreboard Client` | Direct method calls | May use `asyncio.run_coroutine_threadsafe()` if the scoreboard client is async and the handler is sync. |

---

## Suggested Build Order

1. **`obs/client.py` + `obs/scene_controller.py`**
   - Lowest dependency; only needs `obsws-python`.
   - Prove scene switching and source text updates work from a test script.

2. **`cabinets/mapper.py` + extend `RuntimeState`**
   - Add `mode`, `round_assignments`, and `review_queue` to `state.py`.
   - Build round-prep HTML form and POST handler.

3. **`cabinets/worker.py`**
   - Integrate `obs_manager.py` as a library.
   - Start/stop the polling thread safely.
   - Emit `cabinet_update` events to a test UI.

4. **`scoreboard/client.py`**
   - Implement mode-aware `push_score()`.
   - Validate against existing BPL and knockout `server.py` relays.

5. **Score review UI + SocketIO handlers**
   - Build `score_review.html` with editable score cards.
   - Wire "confirm" to trigger Transition 3 and scoreboard push.
   - Add configurable delay inputs (including `-1` for manual advance).

6. **Auto-transition logic**
   - Map state machine outputs to scene transitions.
   - Add delay timers and manual override buttons.

---

## Sources

- `src/app.py` — existing Flask factory and SocketIO setup
- `src/state.py` — existing `RuntimeState` persistence pattern
- `src/config/loader.py` — config loading and Pydantic validation
- `../obs_manager/obs_manager.py` — frame capture, inference integration, and state machine coupling
- `../iidx_bpl_scoreboard/server.py` — WebSocket relay protocol for team mode
- `../iidx_knockout_scoreboard/server.py` — WebSocket relay protocol for individual mode
- `CLAUDE.md` (project) — stack recommendations and version compatibility

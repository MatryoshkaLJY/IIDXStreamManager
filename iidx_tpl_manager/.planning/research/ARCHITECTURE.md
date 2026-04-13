# Architecture Patterns

**Domain:** Python web-based OBS tournament director for beatmania IIDX
**Researched:** 2026-04-14
**Confidence:** HIGH (derived from direct analysis of existing codebase components, protocols, and operator workflows)

---

## Recommended Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Web UI Layer (Flask + SocketIO)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Mode Select │  │  Round Prep  │  │ Live Monitor │  │ Score Review │    │
│  │    Page      │  │    Page      │  │    Page      │  │    Page      │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │             │
│         └─────────────────┴─────────────────┴─────────────────┘             │
│                                    ↓                                        │
│                         ┌────────────────────┐                              │
│                         │   SocketIO Events  │  ← Real-time push to browser │
│                         └────────────────────┘                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                         Application Layer (Python)                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Tournament Director Controller                    │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │    │
│  │  │ ConfigLoader│  │ RoundManager│  │SceneAutomator│  │ScoreManager│ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Polling / Background Thread                       │    │
│  │         (obs_manager.process_frame loop for 4 cabinets)              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────────────┤
│                         External Integration Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   OBS Studio │  │iidx_state_   │  │iidx_score_   │  │ Scoreboards  │    │
│  │  (WebSocket) │  │   reco       │  │   reco       │  │ (WebSocket)  │    │
│  │   Port 4455  │  │  Port 9876   │  │  Port 9877   │  │ 8080 / 8081  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
├─────────────────────────────────────────────────────────────────────────────┤
│                         Data / Config Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                       │
│  │  teams.json  │  │team_schedule.│  │individual_   │                       │
│  │              │  │    json      │  │schedule.json │                       │
│  └──────────────┘  └──────────────┘  └──────────────┘                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Web UI Layer** | Operator-facing pages: mode selection, round prep, live monitoring, score review | Tournament Director Controller via HTTP and SocketIO events |
| **Tournament Director Controller** | Central orchestrator holding current tournament mode, active round, and global state | All sub-managers and the polling thread |
| **ConfigLoader** | Parse and validate `teams.json`, `team_schedule.json`, `individual_schedule.json` | Tournament Director Controller |
| **RoundManager** | Track current round, player-to-cabinet assignments, match metadata | Tournament Director Controller, SceneAutomator, ScoreManager |
| **SceneAutomator** | Decide when to switch OBS scenes and configure gameplay scene sources/groups | Tournament Director Controller, OBS WebSocket, Polling Thread |
| **ScoreManager** | Collect OCR scores, present for review, and push confirmed scores to scoreboards | Tournament Director Controller, Score Review UI, Scoreboard WebSockets |
| **Polling Thread** | Continuously call `obs_manager.process_frame()` for all 4 cabinets | `obs_manager.py` library, feeds events back to SceneAutomator and ScoreManager |
| **obs_manager.py** (reused) | Capture frames from OBS, send to state/score recognition TCP services | OBS WebSocket, `iidx_state_reco`, `iidx_score_reco`, `iidx_state_machine` |

---

## Data Flow

### 1. Setup Flow (Before Broadcast)

```
Operator selects tournament mode
         ↓
ConfigLoader reads appropriate JSON(s)
         ↓
Tournament Director Controller initializes mode state
         ↓
Operator proceeds to Round Prep
         ↓
RoundManager stores player → cabinet mapping
         ↓
SceneAutomator pre-configures gameplay scene text/groups
         ↓
OBS scene is ready for the round
```

### 2. Live Game Flow (Auto-Director Loop)

```
Polling Thread (every ~1s)
    ├── Cabinet 1: capture frame → state reco → state machine
    ├── Cabinet 2: capture frame → state reco → state machine
    ├── Cabinet 3: capture frame → state reco → state machine
    └── Cabinet 4: capture frame → state reco → state machine
                ↓
    State changes emitted via SocketIO to Live Monitor page
                ↓
    SceneAutomator evaluates aggregate state across 4 cabinets
                ↓
    If transition condition met:
        ├── Switch OBS scene (Live ↔ Gameplay ↔ Scoreboard_game)
        └── Emit transition event to Web UI
                ↓
    If any cabinet enters `score` state with valid scores:
        ├── ScoreManager receives OCR results
        ├── Scores displayed in Score Review UI
        └── Operator edits / confirms
                ↓
    On operator confirmation:
        ├── SceneAutomator switches to Scoreboard_web
        ├── Delay N seconds (configurable)
        ├── ScoreManager pushes score to active scoreboard (8080 or 8081)
        ├── Delay M seconds (configurable)
        └── SceneAutomator switches back to Live camera
```

### 3. Scoreboard Push Flow

```
Operator confirms scores in Web UI
         ↓
ScoreManager formats payload based on active mode
         ↓
    If Team Mode:
        └── WebSocket message to BPL scoreboard (port 8080)
                { "cmd": "score", "data": { "round": N, "leftScore": X, "rightScore": Y } }
    If Individual Mode:
        └── WebSocket message to Knockout scoreboard (port 8081)
                { "cmd": "score", "data": { "stage": "...", "group": "...", "round": N, "scores": [...] } }
         ↓
Scoreboard browser source updates on screen
```

---

## Suggested Project Structure

```
iidx_tpl_manager/
├── app.py                      # Flask + SocketIO application entry point
├── config.py                   # App-level configuration (ports, defaults)
├── data/                       # JSON tournament configs (gitignored or tracked)
│   ├── teams.json
│   ├── team_schedule.json
│   └── individual_schedule.json
├── src/
│   ├── __init__.py
│   ├── controller/
│   │   ├── __init__.py
│   │   └── director.py         # TournamentDirector central orchestrator
│   ├── config_loader/
│   │   ├── __init__.py
│   │   └── loader.py           # JSON parsing and validation
│   ├── round_manager/
│   │   ├── __init__.py
│   │   └── round_manager.py    # Round and cabinet assignment state
│   ├── scene_automator/
│   │   ├── __init__.py
│   │   └── automator.py        # OBS scene switching and source setup
│   ├── score_manager/
│   │   ├── __init__.py
│   │   └── score_manager.py    # Score review buffer and scoreboard push
│   ├── obs_client/
│   │   ├── __init__.py
│   │   └── obs_client.py       # Thin wrapper around obs_manager.py + switcher.py logic
│   └── scoreboard_client/
│       ├── __init__.py
│       ├── bpl_client.py       # WebSocket client for port 8080
│       └── knockout_client.py  # WebSocket client for port 8081
├── static/
│   ├── css/
│   └── js/
│       └── monitor.js          # SocketIO client for live updates
├── templates/
│   ├── base.html
│   ├── mode_select.html
│   ├── round_prep.html
│   ├── live_monitor.html
│   └── score_review.html
├── tests/
│   └── ...
└── requirements.txt
```

### Structure Rationale

- **`src/controller/`:** Single source of truth for tournament state. Prevents scattered global variables.
- **`src/config_loader/`:** Isolates JSON schema knowledge. Easy to add validation later.
- **`src/round_manager/`:** Player-to-cabinet mapping changes every round. Keeping it separate makes round transitions explicit.
- **`src/scene_automator/`:** Encapsulates all OBS-side decisions. Mirrors the existing `switcher.py` responsibilities but adds automation logic.
- **`src/score_manager/`:** Handles the human-in-the-loop score confirmation and the final push. Separates transient review state from round state.
- **`src/obs_client/`:** Wraps the reused `obs_manager.py` library so the rest of the app does not depend directly on its threading model.
- **`src/scoreboard_client/`:** Mode-specific protocol implementations. Makes it easy to add new scoreboard types later.

---

## Patterns to Follow

### Pattern 1: Background Thread + SocketIO for Real-Time Push

**What:** Run the 4-cabinet polling loop in a background thread. Emit state and score events via Flask-SocketIO so the browser updates without polling.

**When to use:** Any time the server produces events faster than the user requests them (frame recognition, scene transitions, score arrival).

**Trade-offs:** Keeps UI responsive and enables live dashboards, but requires thread-safe access to shared state.

**Example:**
```python
from flask import Flask
from flask_socketio import SocketIO
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

def polling_loop(director):
    while True:
        results = director.poll_all_machines()
        socketio.emit("machine_update", results)
        socketio.sleep(1.0)

@socketio.on("start_monitoring")
def handle_start_monitoring():
    threading.Thread(target=polling_loop, args=(director,), daemon=True).start()
```

### Pattern 2: State Machine Observer for Scene Transitions

**What:** Treat `iidx_state_machine` outputs as events. A small observer inside `SceneAutomator` maps aggregate cabinet states to scene decisions.

**When to use:** When multiple independent inputs (4 cabinets) must be reduced to a single broadcast decision.

**Trade-offs:** Centralizes transition logic, but the observer must handle edge cases (e.g., 2 cabinets in `play`, 2 in `score`).

**Example transition rules:**
- Any cabinet transitions `live` → `play`: switch to gameplay scene.
- All cabinets in `score` or `blank`: switch to `Scoreboard_game` (intermediate result scene).
- Operator confirms scores: switch to `Scoreboard_web`, then push, then return to `现场摄像`.

### Pattern 3: Human-in-the-Loop Score Buffer

**What:** `ScoreManager` holds unconfirmed scores in memory. The Web UI renders them with editable fields. Only on explicit confirmation does the score leave the buffer and travel to the scoreboard.

**When to use:** AI OCR is imperfect and operator trust is critical.

**Trade-offs:** Adds one step to the flow, but prevents on-air errors.

**Example data structure:**
```python
@dataclass
class PendingScore:
    machine_id: str
    round: int
    raw_scores: dict
    confirmed_scores: Optional[dict] = None
    confirmed: bool = False
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Direct WebSocket Calls from the Polling Thread

**What:** Calling OBS WebSocket or scoreboard WebSocket directly from the background polling thread without going through the controller.

**Why bad:** Creates race conditions, makes transitions hard to trace, and complicates testing.

**Instead:** Polling thread emits events into a thread-safe queue or calls controller methods protected by locks. The controller decides when to act on external services.

### Anti-Pattern 2: Storing OBS Scene Logic in the Frontend

**What:** Having JavaScript decide when to switch scenes by calling a backend endpoint.

**Why bad:** The browser is not the source of truth for game state. A refresh or network hiccup breaks automation.

**Instead:** `SceneAutomator` runs entirely server-side. The frontend is read-only for state and write-only for operator overrides (confirm score, force scene, adjust delays).

### Anti-Pattern 3: Tight Coupling to `obs_manager.py` Internals

**What:** Scattering `OBSManager` instantiation and `process_frame` calls across multiple route handlers.

**Why bad:** `obs_manager.py` may change its API or threading model. Also makes it hard to mock for tests.

**Instead:** Wrap `obs_manager.py` in a thin `OBSClient` class with a stable interface. The rest of the app depends only on `OBSClient`.

---

## Scalability Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 operator, 1 stream | Monolithic Flask app is fine. Run everything on the streaming PC. |
| Multiple concurrent tournaments | Would require splitting the polling thread per event and running separate app instances. Not needed per scope. |
| Higher frame rates | If 1s polling feels sluggish, move to per-cabinet threads with independent intervals, but watch CPU usage from 4x OBS screenshots + inference. |

### Scaling Priorities

1. **First bottleneck:** OBS screenshot latency at high resolution (1920x1080 for score capture). Mitigate by capturing state frames at 224x224 and only capturing full-resolution score frames when the state machine requests them.
2. **Second bottleneck:** TCP inference services under rapid polling. Mitigate by keeping the 1s interval or batching frames if services support it.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| OBS Studio (4455) | WebSocket request/response + event subscription | Use `obsws-python` (already used in `obs_manager.py`). Scene switching is synchronous; source updates are synchronous. |
| `iidx_state_reco` (9876) | TCP socket, 4-byte length prefix + JPEG bytes | Stateless per-frame inference. Already wrapped in `obs_manager.py`. |
| `iidx_score_reco` (9877) | TCP socket, 4-byte length prefix + PNG bytes | Returns JSON with ROI scores and validity flags. Already wrapped in `obs_manager.py`. |
| `iidx_state_machine` | In-process Python import | `obs_manager.py` lazily imports `IIDXStateMachineManager`. State is held in memory. |
| BPL Scoreboard (8080) | WebSocket JSON messages | Init on round load, score on confirmation. Fire-and-forget with optional ack logging. |
| Knockout Scoreboard (8081) | WebSocket JSON messages | Init on tournament start, score per group round, continue on group advance. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Web UI ↔ Controller | HTTP + SocketIO events | Keep payloads small (state labels, score dicts). |
| Controller ↔ SceneAutomator | Direct method calls | SceneAutomator should be idempotent (calling "set gameplay scene" twice is safe). |
| Controller ↔ ScoreManager | Direct method calls + in-memory buffer | ScoreManager exposes `submit_for_review()`, `confirm_score()`, `push_to_scoreboard()`. |
| Controller ↔ Polling Thread | Thread-safe queue or locked shared state | Use `threading.Lock` or `queue.Queue` to pass frame results. |
| Polling Thread ↔ obs_manager.py | Direct method calls | `obs_manager.py` is not thread-safe by design; only the polling thread should use it. |

---

## Build Order Implications

Based on component dependencies, the recommended implementation order is:

1. **ConfigLoader + TournamentDirector shell** — No external dependencies. Establishes the data model.
2. **RoundManager + Round Prep UI** — Depends on ConfigLoader. Enables operator workflow for match setup.
3. **OBSClient wrapper + SceneAutomator (manual switching)** — Depends on OBS WebSocket. Allows operator to cut scenes from the web UI even before automation exists.
4. **Polling Thread + Live Monitor UI** — Depends on OBSClient. Brings in `obs_manager.py`, state reco, and state machine. Enables live state visualization.
5. **SceneAutomator automation rules** — Depends on Polling Thread output. Adds the auto-switching logic.
6. **ScoreManager + Score Review UI** — Depends on Polling Thread score capture. Adds human review.
7. **Scoreboard clients + push integration** — Depends on ScoreManager. Closes the end-to-end loop.
8. **Configurable delays + override controls** — Cross-cutting UI and automator logic. Polish feature.

---

## Sources

- `/home/matryoshka/Downloads/out_frames/iidx_tpl_manager/.planning/PROJECT.md` — requirements and scope
- `/home/matryoshka/Downloads/out_frames/obs_manager/obs_manager.py` — existing capture/recognition integration patterns
- `/home/matryoshka/Downloads/out_frames/tpl_scene_switcher/switcher.py` — existing OBS scene switching and group visibility logic
- `/home/matryoshka/Downloads/out_frames/iidx_state_machine/state_machine.py` — state tracking implementation
- `/home/matryoshka/Downloads/out_frames/iidx_bpl_scoreboard/README.md` and `PROTOCOL.md` — BPL scoreboard WebSocket protocol
- `/home/matryoshka/Downloads/out_frames/iidx_knockout_scoreboard/README.md` — knockout scoreboard WebSocket protocol
- [OBS WebSocket 5.x Protocol Documentation](https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md) — connection handshake, scene transitions, source visibility

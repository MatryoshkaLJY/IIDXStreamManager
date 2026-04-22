# Architecture

**Analysis Date:** 2026-04-22

## Pattern Overview

**Overall:** Monolithic Flask application with background worker threads

**Key Characteristics:**
- Single-process Python web app using Flask + Flask-SocketIO
- Background daemon threads for polling and automation (not async/await based)
- File-based JSON runtime state persistence
- Synchronous OBS WebSocket client (`obsws-python`) matching Flask's threading model
- External AI inference services accessed via TCP through a sibling `obs_manager` package

## Layers

**Web Layer (Flask routes + Jinja2 templates):**
- Purpose: HTTP request handling, server-side rendered HTML UI, REST-ish API endpoints
- Location: `src/app.py`, `src/templates/`, `static/`
- Contains: Route handlers, Pydantic form validation, page rendering
- Depends on: Config loader, OBS client/scene controller, scoreboard pusher, runtime state
- Used by: Browser operator UI

**Configuration Layer:**
- Purpose: Load and validate tournament JSON configs with Pydantic
- Location: `src/config/`
- Contains: Pydantic models (`models.py`), loader with template generation (`loader.py`)
- Depends on: `data/*.json` files on disk
- Used by: `src/app.py` for route logic, round prep player lists, score confirmation

**OBS Integration Layer:**
- Purpose: Connect to OBS Studio via WebSocket v5, validate scenes, switch scenes, monitor cabinet video frames
- Location: `src/obs/`
- Contains: Client wrapper, scene controller, heartbeat monitor, cabinet frame monitor, auto-transition controller
- Depends on: `obsws-python`, sibling `obs_manager` package (for frame capture + AI inference)
- Used by: `src/app.py` for scene buttons, auto-transitions, heartbeat status

**Scoreboard Integration Layer:**
- Purpose: Push confirmed scores to external WebSocket scoreboard servers
- Location: `src/scoreboard/`
- Contains: `ScoreboardPusher` with async WebSocket send wrapped in sync API
- Depends on: `websockets` library
- Used by: `src/app.py` `/confirm_score` route

**State Management Layer:**
- Purpose: Persist runtime state across restarts as JSON on disk
- Location: `src/state.py`
- Contains: `RuntimeState` dataclass, `save_runtime_state()`, `load_runtime_state()`
- Depends on: `runtime/state.json` file
- Used by: Nearly all modules

## Data Flow

**Video Frame → AI Recognition → State Machine → OBS/Scoreboard:**

1. `CabinetMonitor` (background thread in `src/obs/monitor.py`) polls each of 4 cabinets via `OBSManager.process_frame(machine_id)`
2. `OBSManager` (external sibling package) captures a frame from the OBS source, sends it to TCP inference services:
   - State recognition: `127.0.0.1:9876` (`iidx_state_reco`)
   - Score recognition: `127.0.0.1:9877` (`iidx_score_reco`)
3. `iidx_state_machine` (external) runs the state machine over recognized state/score to determine `current_state` (e.g., `play`, `score`, `live`, `blank`)
4. `CabinetMonitor` receives result dict with `state`, `scores`, `score_validation_pending`
5. If `current_state == "score"` and validation is pending, the score data is written to `RuntimeState.pending_scores` and persisted to `runtime/state.json`
6. `CabinetMonitor` emits a SocketIO `cabinet_update` event to the browser
7. Browser score review panel displays pending scores; operator can edit invalid scores inline
8. Operator clicks "Confirm & Push":
   - `/confirm_score` route validates all scores are valid
   - Switches OBS scene to `Scoreboard_web`
   - Computes round points from schedule config + EX scores
   - Calls `ScoreboardPusher.push_team_score()` (port 8080) or `push_individual_score()` (port 8081)
   - Clears `pending_scores` from runtime state

**Auto-Transition Flow:**

1. `AutoTransitionController` (background thread in `src/obs/auto_transition.py`) ticks every 1.0s
2. It maintains `_machine_states` dict updated by `cabinet_update` SocketIO events
3. When all 4 assigned cabinets enter `play`, it switches OBS to the gameplay scene (`SP团队赛` for team mode, `个人赛` for individual)
4. When all cabinets return to `live`/`blank`, it waits `gameplay_hold_delay` then switches back to `现场摄像`
5. If any delay is set to `-1`, automation pauses and emits `proceed_required`; operator must click Proceed
6. Operator can trigger `emergency_live` to force-cut to `现场摄像` and lock automation in `emergency` state

**State Management:**

- `RuntimeState` (dataclass in `src/state.py`) is the single source of truth for:
  - OBS connection settings (`obs_host`, `obs_port`, `obs_password`, `obs_connected`)
  - Tournament mode and round (`mode`, `current_round`)
  - Cabinet assignments (`cabinet_assignments`)
  - Pending scores (`pending_scores`)
  - Automation config (`automation_active`, `automation_state`, `return_to_live_delay`, `gameplay_hold_delay`)
  - Monitoring state (`monitoring_active`, `monitor_interval`)
- Persistence: JSON file at `runtime/state.json`, read/written synchronously on nearly every state change
- No in-memory shared mutable state beyond the dataclass instances; each operation reloads from disk

## Key Abstractions

**OBSClient:**
- Purpose: Lazy-connect wrapper around `obsws_python.ReqClient`
- Location: `src/obs/client.py`
- Pattern: Thin wrapper with connect/disconnect/connected property

**SceneController:**
- Purpose: Validate required scenes exist in OBS and perform scene switches
- Location: `src/obs/scene_controller.py`
- Pattern: Guard class — checks `obs.connected` and `scenes_valid` before every switch

**CabinetMonitor:**
- Purpose: Background polling of 4 cabinets through external `OBSManager`
- Location: `src/obs/monitor.py`
- Pattern: Daemon thread with start/stop lifecycle, `_ensure_obs_manager()` for lazy connection

**AutoTransitionController:**
- Purpose: Automate OBS scene switches based on aggregate cabinet state
- Location: `src/obs/auto_transition.py`
- Pattern: State machine driven by external cabinet updates, with operator override points

**ScoreboardPusher:**
- Purpose: Send score updates to BPL (8080) and knockout (8081) scoreboards
- Location: `src/scoreboard/pusher.py`
- Pattern: Sync facade over async `websockets` connection

## Entry Points

**Flask Application Server:**
- Location: `src/app.py`
- Triggers: `python src/app.py` or external WSGI/ASGI server
- Responsibilities:
  - Create Flask app + SocketIO
  - Instantiate OBS client, scene controller, heartbeat, cabinet monitor, auto-transition controller
  - Eager-load configs and attempt OBS connection inside app context
  - Register all HTTP routes and SocketIO event handlers
  - Run on `0.0.0.0:5002`

**OBSHeartbeat:**
- Location: `src/obs/heartbeat.py`
- Triggers: Started automatically by `create_app()`
- Responsibilities: Emit `obs_status` SocketIO events every 3s, detect disconnections

**CabinetMonitor:**
- Location: `src/obs/monitor.py`
- Triggers: Started/stopped via `/monitor_control` route (not auto-started on launch)
- Responsibilities: Poll 4 cabinets, persist pending scores, emit `cabinet_update` events

**AutoTransitionController:**
- Location: `src/obs/auto_transition.py`
- Triggers: Started automatically by `create_app()`
- Responsibilities: Evaluate aggregate state, trigger scene switches, handle operator proceed/emergency

## Error Handling

**Strategy:** Graceful degradation with user-visible error messages

**Patterns:**
- OBS connection failures are caught, `client.connected` set to `False`, and reflected in UI via SocketIO
- Config validation errors are stored in `app.config["CONFIG_ERROR"]` and rendered on every page
- Scene switch failures return JSON `{"success": False, "error": "..."}` with HTTP 200
- `CabinetMonitor` catches exceptions per-cabinet and continues polling the others
- `ScoreboardPusher` catches exceptions, logs warning, returns `False`

## Cross-Cutting Concerns

**Logging:** Python `logging` module with module-level `logger = logging.getLogger(__name__)`

**Validation:** Pydantic v2 models for config files and form payloads (`src/app.py` form classes, `src/config/models.py`)

**Authentication:** No user authentication; single-operator local app. `SECRET_KEY` from env var for Flask sessions.

---

*Architecture analysis: 2026-04-22*

# External Integrations

**Analysis Date:** 2026-04-22

## OBS WebSocket Connection

**Primary Client: obsws-python**
- Package: obsws-python 1.8.0
- Protocol: OBS WebSocket v5
- Default endpoint: `ws://localhost:4455`
- Key files:
  - `src/obs/client.py` - Lazy-connect wrapper around `obsws_python.ReqClient`
  - `src/obs/scene_controller.py` - Scene validation and switching logic
  - `src/obs/heartbeat.py` - Connection health monitoring (3-second interval)
- Authentication: Password optional, configured via operator UI (`/obs_config` route)
- Methods used:
  - `get_version()` - Health check
  - `get_scene_list(raw=True)` - Validate required scenes exist
  - `set_current_program_scene(name)` - Switch active scene
- Required scenes (defined in `src/obs/scene_controller.py`):
  - `"现场摄像"` (live)
  - `"SP团队赛"` (sp_team)
  - `"DP团队赛"` (dp_team)
  - `"个人赛"` (individual)
  - `"Scoreboard_web"` (scoreboard)

**Secondary OBS Integration: obs_manager (sibling project)**
- Import: `from obs_manager.obs_manager import OBSManager`
- Key file: `src/obs/monitor.py` (lines 11-17)
- Uses `sys.path` manipulation to import from sibling directory
- Provides: frame capture, state machine integration, TCP inference bridging
- Connection: Same OBS WebSocket host/port as primary client
- Additional initialization:
  - State machine config: `iidx_state_machine/state_machine.yaml`
  - Simple mode logging at INFO level

## TCP Inference Services

**State Recognition Service**
- Endpoint: `127.0.0.1:9876`
- Protocol: TCP (handled internally by `OBSManager`)
- Purpose: AI-based game state detection (menu, play, score, etc.)
- Registration: `src/obs/monitor.py` line 98
- Used by: `obs_manager.obs_manager.OBSManager.register_machine()`

**Score Recognition Service**
- Endpoint: `127.0.0.1:9877`
- Protocol: TCP (handled internally by `OBSManager`)
- Purpose: AI-based score extraction from cabinet screens
- Registration: `src/obs/monitor.py` line 99
- Used by: `obs_manager.obs_manager.OBSManager.register_machine()`

**Frame Processing Flow**
1. `CabinetMonitor._run()` polls each of 4 cabinets (`IIDX#1` through `IIDX#4`)
2. Calls `obs.process_frame(machine_id)` which internally:
   - Captures frame from OBS source
   - Sends to state inference (port 9876)
   - Sends to score inference (port 9877)
3. Results emitted via Socket.IO as `cabinet_update` events

## WebSocket Scoreboards

**BPL Team Scoreboard**
- URI: `ws://localhost:8080`
- Protocol: WebSocket (client via `websockets` library)
- Key file: `src/scoreboard/pusher.py` (lines 10, 18-28)
- Message format:
  ```json
  {"cmd": "score", "data": {"round": N, "leftScore": N, "rightScore": N}}
  ```
- Triggered by: `/confirm_score` route when mode is `"team"`
- Scoring logic:
  - 1v1: Winner gets `round.points`, loser gets 0 (based on EX score comparison)
  - 2v2: Ranked scoring (1st=3, 2nd=2, 3rd=1, 4th=0) aggregated per side

**Knockout Individual Scoreboard**
- URI: `ws://localhost:8081`
- Protocol: WebSocket (client via `websockets` library)
- Key file: `src/scoreboard/pusher.py` (lines 11, 30-47)
- Message format:
  ```json
  {"cmd": "score", "data": {"stage": "quarterfinal", "group": "A", "round": N, "scores": [...]}}
  ```
- Triggered by: `/confirm_score` route when mode is `"individual"`
- Stage mapping: groups A-D = quarterfinal, E-F = semifinal, finals = final

**Scoreboard Pusher Implementation**
- Class: `ScoreboardPusher` in `src/scoreboard/pusher.py`
- Uses `asyncio.run()` to bridge sync Flask context to async WebSocket calls
- One-shot connections: opens, sends, closes for each push
- No retry logic; failures logged as warnings

## Flask / Flask-SocketIO Setup

**Application Factory**
- Function: `create_app(return_socketio=False)` in `src/app.py` (lines 69-671)
- Template folder: `src/templates/`
- Static folder: `static/`
- Secret key: `os.environ.get("SECRET_KEY", "dev-secret-change-in-production")`

**Socket.IO Server Configuration**
- Initialized: `SocketIO(app, cors_allowed_origins="*")` (line 78)
- Transport: WebSocket (with fallback to polling)
- Events handled:
  - `obs_reconnect` - Manual OBS reconnection trigger
  - `cabinet_update` - Forwarded to `AutoTransitionController`
- Events emitted:
  - `obs_status` - Connection and scene validation state
  - `monitoring_status` - Monitor start/stop state
  - `automation_status` - Automation state changes
  - `proceed_required` - Manual proceed needed (-1 delay)
  - `auto_transition` - Scene transition notifications
  - `scores_pushed` - Score confirmation
  - `scoreboard_delay_updated` - Delay config changes
  - `automation_delays_updated` - Delay config changes
  - `mode_changed` - Tournament mode changes
  - `config_uploaded` - Config file upload confirmation
  - `round_saved` - Round assignment saved
  - `round_changed` - Round navigation

**Background Threads**
- `OBSHeartbeat` - 3-second interval, monitors OBS connection health
- `CabinetMonitor` - Configurable interval (default 1.0s), polls 4 cabinets
- `AutoTransitionController` - 1-second interval, evaluates scene transitions
- All threads are daemonized; terminate with main process

## Data Storage

**Local JSON Files**
- `data/teams.json` - Team roster config (Pydantic-validated)
- `data/team_schedule.json` - Weekly match schedule (Pydantic-validated)
- `data/individual_schedule.json` - Group schedule (Pydantic-validated)
- `runtime/state.json` - Runtime state persistence (dataclass-based)
- No database; all state is file-based

**File Storage:**
- Local filesystem only
- Config backups: `.bak` suffix created on upload (`src/app.py` lines 416-418)

## Authentication & Identity

**Auth Provider:** None
- No user authentication system
- Single-operator local application
- OBS password stored in plaintext in `runtime/state.json`

## Monitoring & Observability

**Error Tracking:**
- Python `logging` module with module-level loggers
- Log levels: WARNING for recoverable issues (connection failures, inference errors)
- Console output: JSON lines per cabinet frame (`src/obs/monitor.py` line 157)

**Logs:**
- Application logs to stdout/stderr
- No structured logging or log aggregation configured

## CI/CD & Deployment

**Hosting:** Local execution only
- Dev server: `socketio.run(app, host="0.0.0.0", port=5002, allow_unsafe_werkzeug=True)`
- No production WSGI server configuration (gunicorn/uvicorn available but unused)

**CI Pipeline:** None detected

## Environment Configuration

**Required runtime services:**
- OBS Studio with WebSocket v5 on configured host:port (default localhost:4455)
- TCP state inference on 127.0.0.1:9876
- TCP score inference on 127.0.0.1:9877
- WebSocket BPL scoreboard on localhost:8080
- WebSocket knockout scoreboard on localhost:8081

**Optional env vars:**
- `SECRET_KEY` - Flask session secret (falls back to dev default)

**Secrets location:**
- OBS password stored in `runtime/state.json` (plaintext)
- No `.env` file or secret management detected

## Webhooks & Callbacks

**Incoming:**
- Socket.IO events from operator browser (obs_reconnect, cabinet_update)
- HTTP POST routes for operator actions

**Outgoing:**
- WebSocket messages to scoreboards (ports 8080, 8081)
- OBS WebSocket scene switch commands
- No external HTTP webhooks

## Integration Architecture Diagram

```
Operator Browser  <--WebSocket/Socket.IO-->  Flask App (port 5002)
                                                    |
        +------------------+------------------+------------------+
        |                  |                  |                  |
   OBS WebSocket      obs_manager        TCP Inference      Scoreboard WS
   (port 4455)       (sibling proj)     (ports 9876,9877)   (ports 8080,8081)
        |                  |                  |                  |
   OBS Studio      State Machine       AI Models (external)   Scoreboard UIs
```

---

*Integration audit: 2026-04-22*

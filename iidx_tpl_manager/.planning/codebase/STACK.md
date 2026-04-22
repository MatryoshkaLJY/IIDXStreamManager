# Technology Stack

**Analysis Date:** 2026-04-22

## Languages

**Primary:**
- Python 3.13.5 - All backend logic, OBS integration, WebSocket services, and automation

**Secondary:**
- JavaScript (ES6) - Frontend real-time UI via Socket.IO client (`static/js/operator.js`)
- HTML (Jinja2 templates) - Server-rendered operator UI pages (`src/templates/*.html`)
- CSS3 - Custom dark-themed styling (`static/css/main.css`)

## Runtime

**Environment:**
- Python 3.13+ (Anaconda distribution at `/home/matryoshka/anaconda3/bin/python3`)
- No `.python-version` or `.nvmrc` file present

**Package Manager:**
- pip (via Anaconda) - No `requirements.txt`, `pyproject.toml`, `setup.py`, or `uv.lock` found in repo
- Lockfile: Not present in repository

## Frameworks

**Core Web:**
- Flask 3.1.3 - WSGI web framework for the operator control panel
  - Entry point: `src/app.py` (line 71-75)
  - Server-rendered HTML with Jinja2 templating
  - Dev server runs on `0.0.0.0:5002` (line 676)
- Flask-SocketIO 5.6.1 - Real-time bidirectional WebSocket communication for UI push updates
  - Initialized in `src/app.py` (line 78)
  - CORS allowed origins: `"*"`
  - Used for: obs_status, cabinet_update, automation_status, proceed_required, auto_transition, scores_pushed, scoreboard_delay_updated, mode_changed, config_uploaded, round_saved, round_changed, monitoring_status

**Testing:**
- pytest 8.3.4 - Unit and integration test runner
  - Config: No dedicated config file; uses default pytest discovery
  - Test files: `tests/test_*.py`
  - Run command: `pytest` (from project root)

**Build/Dev:**
- Werkzeug 3.1.3 - WSGI utilities (Flask dependency)
- Jinja2 3.1.6 - Server-side HTML templating engine

## Key Dependencies

**Critical - OBS Integration:**
- obsws-python 1.8.0 - OBS WebSocket v5 client for scene switching and connection management
  - Used in: `src/obs/client.py` (lines 3, 22-26)
  - Provides: `ReqClient`, `OBSSDKError`, `OBSSDKRequestError`
  - Targets OBS Studio 28+ with built-in WebSocket v5

**Critical - Real-time Communication:**
- python-socketio 5.16.1 - Socket.IO engine (Flask-SocketIO dependency)
- websockets 16.0 - Async-native WebSocket client for scoreboard connections
  - Used in: `src/scoreboard/pusher.py` (lines 6, 57-58)
  - Protocol: WebSocket to localhost:8080 and localhost:8081

**Critical - Data Validation:**
- pydantic 2.13.0 - Runtime data validation for config files and form inputs
  - Used in: `src/config/models.py`, `src/config/loader.py`, `src/app.py` (form validation classes)
  - Models: `TeamsConfig`, `TeamScheduleConfig`, `IndividualScheduleConfig`, `OBSConfigForm`, `ModeForm`, etc.

**Infrastructure:**
- httpx 0.28.1 - Modern HTTP client (available but not actively used in current codebase)
- aiohttp 3.11.10 - Async HTTP client (available but not actively used)
- flask-cors 6.0.2 - CORS support for Flask (available)

**External Sibling Projects (not pip packages):**
- `obs_manager` - Sibling directory project providing `OBSManager` class
  - Imported in: `src/obs/monitor.py` (lines 11-17)
  - Provides: TCP inference bridging, state machine initialization, frame processing
- `iidx_state_machine` - Sibling directory project providing state machine YAML config
  - Referenced in: `src/state.py` (line 29), `src/obs/monitor.py` (line 23)

## Configuration

**Environment:**
- `SECRET_KEY` read from environment variable, falls back to `"dev-secret-change-in-production"` (`src/app.py` line 76)
- No `.env` file present in repository
- Runtime state persisted to JSON: `runtime/state.json`

**Build:**
- No build step required - pure Python runtime
- No transpilation, bundling, or compilation
- Static assets served directly by Flask (`static/` folder)

**Config Files:**
- `data/teams.json` - Team definitions with players and colors
- `data/team_schedule.json` - Weekly match schedules with rounds
- `data/individual_schedule.json` - Group-based individual tournament schedule
- Runtime state: `runtime/state.json` (auto-created)

## Platform Requirements

**Development:**
- Python 3.13+
- OBS Studio 28+ with WebSocket v5 enabled on port 4455 (default)
- TCP inference services on ports 9876 (state) and 9877 (score)
- WebSocket scoreboard servers on ports 8080 (BPL) and 8081 (knockout)

**Production:**
- Runs locally on streaming PC alongside OBS
- Single-operator local web application
- No containerization or cloud deployment configured

---

*Stack analysis: 2026-04-22*

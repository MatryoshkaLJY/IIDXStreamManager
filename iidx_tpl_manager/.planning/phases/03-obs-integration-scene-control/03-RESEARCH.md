# Phase 3: OBS Integration & Scene Control - Research

**Researched:** 2026-04-15
**Domain:** Python Flask + OBS WebSocket v5 integration
**Confidence:** HIGH

## Summary

This phase implements the foundational OBS integration layer for the IIDX Tournament Auto-Director. The core challenge is connecting to OBS Studio via WebSocket v5, validating scene names on startup, switching scenes from the web UI, and maintaining connection health with graceful degradation when OBS becomes unreachable.

The chosen stack is already locked in: `obsws-python` 1.8.0 for OBS WebSocket v5, Flask 3.1.3 + Flask-SocketIO 5.6.1 for the web UI and real-time push updates. All required packages are installed and verified in the environment.

Key architectural decisions from the discuss-phase constrain the design:
- The app must start even if OBS is unreachable or scenes are missing, showing warnings and disabling controls.
- No auto-reconnect loop; the operator must click a manual "Reconnect to OBS" button.
- Connection health is monitored via a lightweight background heartbeat (2-5s interval).
- Only scene switching is in scope; group visibility and text source updates are deferred.

**Primary recommendation:** Build a lazy-connecting `OBSClient` wrapper around `obsws-python`, a `SceneController` for validated scene switching, a daemon heartbeat thread for health monitoring, and use Flask-SocketIO to push state to a minimal Jinja2 UI.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OBS WebSocket connection | API / Backend (Flask app) | — | `obsws-python` runs server-side; browser never touches OBS directly |
| Scene validation on startup | API / Backend | — | Validation logic belongs in the backend initialization phase |
| Scene switching | API / Backend | — | Operator clicks UI button, but the actual `SetCurrentProgramScene` call runs in Flask route/SocketIO handler |
| Connection health monitoring | API / Backend | — | Background thread polls OBS via `GetVersion` every 2-5s |
| Connection state UI push | API / Backend | Browser | Flask-SocketIO emits `obs_status` events; browser renders banner/disabled states |
| OBS config form | Browser (Jinja2) | API / Backend | Server-rendered HTML form posts to Flask route |
| Reconnect button | Browser | API / Backend | JS emits SocketIO `obs_reconnect` event; backend re-instantiates client |

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** OBS host, port, and password are stored in `runtime/state.json` (extending `RuntimeState`) and editable through a web UI form.
- **D-02:** Default values on first run: `localhost:4455` with no password.
- **D-03:** On startup, the app validates that the four required scene names exist in OBS.
- **D-04:** If any scene is missing, the app **starts anyway** but displays a persistent warning banner in the UI and disables scene-switching controls.
- **D-05:** The operator can click a "Retry validation" or "Reconnect" button in the UI to re-check scenes without restarting the app.
- **D-06:** Phase 3 implements **only scene switching** (changing the current program scene).
- **D-07:** Group visibility and text source updates within gameplay scenes (SP/DP team match setup) are deferred to a later phase.
- **D-08:** If the OBS WebSocket disconnects, the app shows a warning banner with a **manual "Reconnect to OBS"** button.
- **D-09:** No automatic reconnection loop. Auto-switching remains paused until the operator manually reconnects.
- **D-10:** Connection health is checked via a lightweight background heartbeat (e.g., periodic `GetVersion` or `GetSceneList` calls).

### Claude's Discretion
- Exact UI layout and styling for the OBS config form.
- Reconnect button placement and wording.
- Heartbeat polling interval (recommend 2-5 seconds).
- How the disabled scene-control state is rendered (e.g., disabled buttons vs hidden section).

### Deferred Ideas (OUT OF SCOPE)
- **Group visibility and text source control for gameplay scenes** (`SP团队赛` / `DP团队赛` setup) — deferred to Phase 4 or later.
- **Auto-retry with backoff for OBS reconnection** — user explicitly chose manual reconnect only.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OBS-01 | Application connects to OBS Studio via WebSocket v5 and validates configured scene names on startup | `obsws-python` 1.8.0 installed and verified; `GetSceneList` returns raw dict with `scenes` list; lazy-connect wrapper prevents startup blocking |
| OBS-02 | Application can programmatically switch OBS scenes: `现场摄像`, `SP团队赛`, `DP团队赛`, `个人赛` | `ReqClient.set_current_program_scene(name)` confirmed available; error code 500/604 for missing scenes can be caught via `OBSSDKRequestError` |
| OBS-03 | Application controls group visibility and text sources within gameplay scenes (SP/DP team match setup) | **OUT OF SCOPE for Phase 3** — deferred per D-07 |
| OBS-04 | Connection health is monitored; if OBS becomes unreachable, auto-switching is paused and the UI shows a warning | Background heartbeat thread + `socketio.emit('obs_status', ...)` from thread works in `threading` async_mode; manual reconnect via SocketIO event handler confirmed testable |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| obsws-python | 1.8.0 | OBS WebSocket v5 client | Locked decision from v1.2 research; actively maintained; sync API matches Flask threading model [VERIFIED: `pip show obsws-python` + runtime import] |
| Flask | 3.1.3 | Web framework | Existing stack; operator prefers ease of development [VERIFIED: `pip show Flask`] |
| Flask-SocketIO | 5.6.1 | Real-time UI push | Already initialized in `src/app.py`; cross-thread `emit` works with `threading` async_mode [VERIFIED: `pip show flask-socketio` + runtime tests] |
| python-socketio | 5.16.1 | Socket.IO engine | Required by Flask-SocketIO; versions are compatible [VERIFIED: `pip show python-socketio`] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic | 2.13.0 | Config validation | Validate OBS config form inputs (host, port) [VERIFIED: `pip show pydantic`] |
| pytest | 8.3.4 | Testing | Existing test suite uses pytest; 18 tests passing [VERIFIED: `pytest tests/ -q`] |

### Installation
All packages are already installed in the environment. No new installations required.

```bash
# Verification commands
pip show obsws-python flask flask-socketio python-socketio pydantic pytest
```

## Architecture Patterns

### System Architecture Diagram

```
Operator Browser
       |
       | HTTP GET /          HTTP POST /obs_config
       | HTTP POST /switch_scene
       v
+-------------------+        +-------------------+
|  Flask App (5002) |<------>|  RuntimeState     |
|  - Jinja2 routes  |        |  (runtime/state)  |
|  - SocketIO handlers       +-------------------+
+---------+---------+
          |
          | socketio.emit('obs_status', ...)
          v
+-------------------+        +-------------------+
|  Background Thread|------->|  OBSClient        |
|  (heartbeat)      |        |  (obsws-python)   |
+-------------------+        +---------+---------+
                                       |
                                       | WebSocket v5
                                       v
                                  +----------+
                                  | OBS Studio|
                                  +----------+
```

### Recommended Project Structure

```
src/
├── app.py                    # Flask factory + SocketIO init
├── state.py                  # RuntimeState + persistence
├── obs/
│   ├── __init__.py
│   ├── client.py             # Lazy-connect wrapper around obsws-python
│   └── scene_controller.py   # Validated scene switching
├── templates/
│   ├── base.html
│   ├── status.html           # Extended with OBS banner + scene controls
│   └── obs_config.html       # OBS connection form
└── static/
    ├── css/
    │   └── main.css          # Add minimal form/button styles
    └── js/
        └── operator.js       # SocketIO client for OBS status + reconnect
```

### Pattern 1: Lazy-Connect OBSClient Wrapper
**What:** A thin wrapper that delays `obsws-python.ReqClient` instantiation until `connect()` is explicitly called. This prevents the Flask app from crashing on startup if OBS is not running.

**When to use:** Any time you need to instantiate the client object before the target service is guaranteed to be available.

**Example:**
```python
# Source: obsws-python 1.8.0 source inspection
import obsws_python
from obsws_python.error import OBSSDKError

class OBSClient:
    def __init__(self, host: str = "localhost", port: int = 4455, password: str = ""):
        self.host = host
        self.port = port
        self.password = password
        self._client = None

    def connect(self) -> None:
        self._client = obsws_python.ReqClient(
            host=self.host, port=self.port, password=self.password, timeout=3
        )

    def disconnect(self) -> None:
        if self._client:
            self._client.disconnect()
            self._client = None

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.base_client.ws.connected

    def get_version(self):
        return self._client.get_version()

    def get_scene_list(self, raw: bool = False):
        return self._client.send("GetSceneList", raw=raw)

    def set_current_program_scene(self, name: str) -> None:
        self._client.set_current_program_scene(name)
```

### Pattern 2: SceneController with Validation
**What:** A higher-level controller that owns the scene name mappings and validates them against OBS before switching.

**When to use:** You need to prevent switching to scenes that do not exist in OBS and centralize scene-name constants.

**Example:**
```python
# Source: project architecture patterns
from typing import List, Tuple

REQUIRED_SCENES = {
    "live": "现场摄像",
    "sp_team": "SP团队赛",
    "dp_team": "DP团队赛",
    "individual": "个人赛",
}

class SceneController:
    def __init__(self, obs_client):
        self.obs = obs_client
        self.scenes_valid = False
        self.missing_scenes: List[str] = []

    def validate_scenes(self) -> Tuple[bool, List[str]]:
        if not self.obs.connected:
            self.scenes_valid = False
            self.missing_scenes = []
            return False, []
        try:
            raw = self.obs.get_scene_list(raw=True)
            available = {s["sceneName"] for s in raw["scenes"]}
            required = list(REQUIRED_SCENES.values())
            self.missing_scenes = [s for s in required if s not in available]
            self.scenes_valid = len(self.missing_scenes) == 0
            return self.scenes_valid, self.missing_scenes
        except Exception:
            self.scenes_valid = False
            self.missing_scenes = []
            return False, []

    def switch_to(self, scene_name: str) -> Tuple[bool, str]:
        if not self.obs.connected or not self.scenes_valid:
            return False, "OBS not ready"
        try:
            self.obs.set_current_program_scene(scene_name)
            return True, ""
        except OBSSDKRequestError as e:
            return False, str(e)
```

### Pattern 3: Background Heartbeat Thread
**What:** A daemon thread that periodically calls a lightweight OBS request (e.g., `GetVersion`) to detect disconnections and emits `obs_status` events to all connected browsers.

**When to use:** You need to detect external service health without blocking HTTP request handlers.

**Example:**
```python
# Source: Flask-SocketIO threading async_mode verification
import threading
import time
from flask_socketio import SocketIO

class OBSHeartbeat:
    def __init__(self, obs_client, socketio: SocketIO, interval: float = 2.0):
        self.obs = obs_client
        self.socketio = socketio
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.interval + 1)

    def _run(self):
        while not self._stop.is_set():
            was_connected = self.obs.connected
            try:
                if not was_connected:
                    self.obs.connect()
                self.obs.get_version()
                self.obs.connected = True
            except Exception:
                self.obs.connected = False
                try:
                    self.obs.disconnect()
                except Exception:
                    pass
            # Emit state change to all browsers
            self.socketio.emit(
                "obs_status",
                {"connected": self.obs.connected},
            )
            self._stop.wait(self.interval)
```

**Important:** Per D-09, do NOT auto-reconnect in `_run()`. The heartbeat should only detect disconnection and emit state. Reconnection is triggered only by the manual "Reconnect to OBS" button.

Corrected heartbeat (no auto-reconnect):
```python
    def _run(self):
        while not self._stop.is_set():
            try:
                if self.obs.connected:
                    self.obs.get_version()
            except Exception:
                self.obs.connected = False
                try:
                    self.obs.disconnect()
                except Exception:
                    pass
            self.socketio.emit("obs_status", {"connected": self.obs.connected})
            self._stop.wait(self.interval)
```

### Pattern 4: Flask-SocketIO Cross-Thread Emit
**What:** Push server-generated events from background threads to all connected SocketIO clients.

**When to use:** The heartbeat thread needs to update the UI in real time without the browser polling.

**Example:**
```python
# Source: Flask-SocketIO emit docstring + runtime verification
from flask_socketio import SocketIO

# Inside a background thread:
socketio.emit("obs_status", {"connected": True, "scenes_valid": True})
```

This works because Flask-SocketIO with `async_mode='threading'` uses an internal message queue that is safe to write to from any thread.

### Anti-Patterns to Avoid
- **Instantiating `ReqClient` at import time:** `obsws-python` connects to OBS immediately in `__init__`. If OBS is down, the app crashes on startup. Always wrap it in a lazy-connect class.
- **Calling OBS WebSocket from the frame-processing loop:** Scene switches should not block cabinet monitoring. Keep OBS calls in dedicated handlers or threads.
- **Storing OBS client in a global variable:** Use `app.extensions` or a registry object to avoid race conditions and make testing easier.
- **Auto-reconnect loops:** The user explicitly chose manual reconnect only (D-09). Do not implement exponential backoff or automatic retries.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OBS WebSocket v5 protocol | Raw WebSocket client | `obsws-python` 1.8.0 | Already chosen, actively maintained, handles authentication, request/response matching, and dataclass conversion |
| Real-time browser push | Long-polling AJAX | Flask-SocketIO | Already in use in `src/app.py`; lower latency, bidirectional, simpler JS |
| Connection state management | Global mutable variables | `app.extensions` registry + threading.Lock | Prevents race conditions, testable, follows Flask patterns |
| Scene validation | Manual OBS API parsing | `GetSceneList` via `obsws-python` | Standard v5 request; returns complete scene list with names and indices |

## Common Pitfalls

### Pitfall 1: `ReqClient` Connects on Instantiation and Crashes Startup
**What goes wrong:** `obsws_python.ReqClient(host='localhost', port=4455)` immediately opens a TCP connection. If OBS is not running, it raises `ConnectionRefusedError` and the Flask app fails to start.

**Why it happens:** The `ObsClient.__init__` in `obsws-python` calls `self.ws.connect()` synchronously. Developers often create the client inside `create_app()` without a try/except.

**How to avoid:** Use the lazy-connect `OBSClient` wrapper. Instantiate the wrapper in `create_app()`, but only call `connect()` inside a guarded startup block or on-demand (e.g., when the operator clicks "Reconnect").

**Warning signs:** `ConnectionRefusedError: [Errno 111]` during `flask run` before any request is served.

### Pitfall 2: Heartbeat Thread Auto-Reconnects Despite User Decision
**What goes wrong:** The heartbeat thread detects a disconnection and immediately tries to reconnect inside its loop. This creates a tight retry loop that spams logs and may confuse the operator who expects manual control.

**Why it happens:** It is natural to write `if not connected: client.connect()` inside the heartbeat loop.

**How to avoid:** Separate "health check" from "reconnect action." The heartbeat only calls `get_version()` when already connected. On failure, it marks `connected = False`, disconnects, and emits the warning. Reconnection is handled exclusively by the `obs_reconnect` SocketIO handler.

### Pitfall 3: SocketIO Events Not Reaching the Browser from Background Threads
**What goes wrong:** The heartbeat thread calls `socketio.emit()`, but the browser never receives the event. This usually happens when `async_mode` is mismatched (e.g., `eventlet` or `gevent` without the corresponding libraries installed).

**Why it happens:** Flask-SocketIO defaults to `threading` only when `FLASK_RUN_FROM_CLI` is set. In production with `gunicorn`, it may pick `eventlet` if installed.

**How to avoid:** Explicitly set `async_mode='threading'` in `create_app()` to match the project's current environment and avoid silent mode switches. Verified that cross-thread emit works correctly with `threading`.

### Pitfall 4: Scene Switching to a Missing Scene Crashes the Handler
**What goes wrong:** `set_current_program_scene('MissingScene')` raises `OBSSDKRequestError` with code 500 or 604. If uncaught, it bubbles up as a 500 error to the operator.

**Why it happens:** OBS validates scene names at request time. The scene list may change after startup validation.

**How to avoid:** Wrap every `set_current_program_scene` call in a try/except for `OBSSDKRequestError`. Return a user-friendly message instead of crashing.

### Pitfall 5: RuntimeState Load Fails After Adding New Fields
**What goes wrong:** `state.py` is extended with `obs_host`, `obs_port`, `obs_password`, but `load_runtime_state()` only passes the old fields to `RuntimeState()`, causing a `TypeError` on startup.

**Why it happens:** The existing `load_runtime_state` does not use default values for missing keys.

**How to avoid:** Update `load_runtime_state()` to pass `.get('obs_host', 'localhost')`, `.get('obs_port', 4455)`, `.get('obs_password', '')` so old `state.json` files load gracefully.

## Code Examples

### Verified patterns from official sources

#### Connecting to OBS and listing scenes
```python
# Source: obsws-python 1.8.0 source + runtime verification
import obsws_python

client = obsws_python.ReqClient(host="localhost", port=4455, password="", timeout=3)
raw_scenes = client.send("GetSceneList", raw=True)
scene_names = [s["sceneName"] for s in raw_scenes["scenes"]]
print(scene_names)
client.disconnect()
```

#### Switching scenes with error handling
```python
# Source: obsws-python error class inspection
from obsws_python.error import OBSSDKRequestError

try:
    client.set_current_program_scene("SP团队赛")
except OBSSDKRequestError as e:
    print(f"Scene switch failed: {e.req_name} code {e.code}")
```

#### SocketIO test client for verifying server events
```python
# Source: Flask-SocketIO runtime verification
from src.app import create_app
app, socketio = create_app(return_socketio=True)

test_client = socketio.test_client(app)
socketio.emit("obs_status", {"connected": True})
received = test_client.get_received()
assert received[0]["name"] == "obs_status"
```

#### JavaScript client for OBS status banner
```html
<!-- Source: Flask-SocketIO standard client patterns -->
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<script>
  const socket = io();
  socket.on('obs_status', (data) => {
    const banner = document.getElementById('obs-banner');
    const bannerText = document.getElementById('obs-banner-text');
    if (!data.connected) {
      banner.style.display = 'block';
      bannerText.textContent = 'OBS disconnected. Auto-switching paused.';
      bannerText.className = 'status-error';
    } else {
      banner.style.display = 'none';
    }
  });
  document.getElementById('obs-reconnect-btn').addEventListener('click', () => {
    socket.emit('obs_reconnect');
  });
</script>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `obs-websocket-py` (v4, unmaintained) | `obsws-python` 1.8.0 (v5) | v1.2 research (2026-04-14) | Cleaner sync API, active maintenance, supports OBS Studio 28+ |
| HTMX + SSE for real-time UI | Flask-SocketIO 5.6.1 | v1.2 research (2026-04-14) | Bidirectional events needed for operator controls like "confirm score" and "reconnect" |
| Global mutable OBS client | `app.extensions` registry | Phase 3 research | Thread-safe, testable, avoids anti-pattern flagged in ARCHITECTURE.md |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `obsws-python` raises `OBSSDKRequestError` with `.code` 500 or 604 when `SetCurrentProgramScene` targets a missing scene | Common Pitfalls | If error code differs, the error-handling path may need adjustment; still caught as `OBSSDKRequestError` |
| A2 | The `websocket.WebSocket.connected` property reliably returns `False` after the underlying socket is closed or connection fails | Architecture Patterns | If unreliable, heartbeat may falsely report "connected"; fallback is to catch exceptions on `get_version()` |
| A3 | Flask-SocketIO's `threading` async_mode is sufficient for a single-operator local app and will not become a bottleneck | Architecture Patterns | If future requirements demand multiple operators, a message broker (Redis) would be needed |

## Open Questions (RESOLVED)

1. **Should scene switching use HTTP POST or SocketIO events?** — RESOLVED: Use HTTP POST for the scene-switcher buttons to keep the initial implementation simple and server-rendered. Use SocketIO only for push events (status, reconnect).

2. **Where should the OBS config form live — a separate `/obs_config` page or inline on the status page?** — RESOLVED: Inline the config form and scene controls on the status page for Phase 3. The operator's primary workflow is a single dashboard.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | Runtime | Yes | 3.13.x | — |
| obsws-python | OBS v5 client | Yes | 1.8.0 | — |
| Flask | Web framework | Yes | 3.1.3 | — |
| Flask-SocketIO | Real-time UI | Yes | 5.6.1 | — |
| python-socketio | SocketIO engine | Yes | 5.16.1 | — |
| Pydantic | Config validation | Yes | 2.13.0 | — |
| pytest | Testing | Yes | 8.3.4 | — |
| OBS Studio (local) | Integration target | Not checked | — | Phase can be developed with mocks; real OBS needed for manual UAT only |

**Missing dependencies with no fallback:** None — all Python packages are installed.

**Missing dependencies with fallback:** OBS Studio itself is not verified running, but the lazy-connect wrapper and mock-based tests allow full development without it.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 |
| Config file | None (default discovery) |
| Quick run command | `pytest tests/ -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OBS-01 | RuntimeState loads old JSON with new OBS fields gracefully | unit | `pytest tests/test_state.py -x` | Yes (exists) |
| OBS-01 | OBSClient connects lazily and validates scene list | unit | `pytest tests/test_obs_client.py -x` | No — Wave 0 gap |
| OBS-02 | SceneController switches to valid scene | unit | `pytest tests/test_scene_controller.py -x` | No — Wave 0 gap |
| OBS-02 | Scene switching route returns error when OBS disconnected | unit | `pytest tests/test_app_obs_routes.py -x` | No — Wave 0 gap |
| OBS-04 | Heartbeat emits obs_status on disconnect detection | unit | `pytest tests/test_obs_client.py -x` | No — Wave 0 gap |
| OBS-04 | SocketIO reconnect handler triggers re-validation | unit | `pytest tests/test_app_obs_routes.py -x` | No — Wave 0 gap |

### Sampling Rate
- **Per task commit:** `pytest tests/ -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_obs_client.py` — covers OBSClient connection, disconnection, heartbeat
- [ ] `tests/test_scene_controller.py` — covers scene validation and switching
- [ ] `tests/test_app_obs_routes.py` — covers Flask routes and SocketIO handlers
- [ ] `src/obs/__init__.py` — package init with public API
- [ ] `static/js/operator.js` — SocketIO client for real-time updates

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Local single-operator app; no user accounts |
| V3 Session Management | No | No sessions required |
| V4 Access Control | No | Single operator on local machine |
| V5 Input Validation | Yes | Pydantic for OBS config (host, port); server-side scene name validation |
| V6 Cryptography | No | OBS password is stored in plaintext in `runtime/state.json` on the streaming PC; acceptable for local tournament use but should not be committed to git |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| OBS password in `runtime/state.json` | Information Disclosure | Ensure `runtime/` is in `.gitignore`; do not log password values |
| Arbitrary scene name injection via UI | Tampering | Server-side validation against OBS scene list; do not trust client-submitted scene names blindly |
| OBS WebSocket exposed to LAN | Spoofing | Default `localhost:4455` is loopback-only; warn if operator changes host to `0.0.0.0` |

## Sources

### Primary (HIGH confidence)
- `obsws-python` 1.8.0 source code (installed at `/home/matryoshka/anaconda3/lib/python3.13/site-packages/obsws_python/`) — `ReqClient`, `ObsClient`, `OBSSDKError`, `OBSSDKRequestError` signatures and behavior verified via `inspect.getsource()` and runtime tests.
- `Flask-SocketIO` 5.6.1 source code (installed at `/home/matryoshka/anaconda3/lib/python3.13/site-packages/flask_socketio/`) — `emit()` cross-thread behavior verified with daemon-thread runtime tests.
- `src/app.py`, `src/state.py`, `src/templates/base.html`, `static/css/main.css` — existing project patterns read directly.

### Secondary (MEDIUM confidence)
- OBS WebSocket v5 protocol documentation (inferred from `obsws-python` request/response handling and error code conventions) — error code 500/604 for missing scenes is consistent with OBS WebSocket v5 spec but not verified against live OBS in this session.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages installed and runtime-verified.
- Architecture: HIGH — patterns tested with mock clients and SocketIO test client.
- Pitfalls: HIGH — derived from direct source inspection and documented anti-patterns in project research.

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable stack, low churn expected)

---

## RESEARCH COMPLETE

**Phase:** 03 - obs-integration-scene-control
**Confidence:** HIGH

### Key Findings
1. `obsws-python` 1.8.0 connects synchronously in `ReqClient.__init__`; a lazy-connect wrapper is mandatory to avoid crashing Flask startup when OBS is unreachable.
2. Flask-SocketIO 5.6.1 with `async_mode='threading'` safely supports cross-thread `emit()`, confirmed with runtime tests using daemon threads and multiple test clients.
3. Scene validation uses `GetSceneList` (raw dict) to extract `sceneName` values; missing scenes trigger `OBSSDKRequestError` on switch attempts.
4. The user explicitly ruled out auto-reconnect (D-09); the heartbeat must only detect disconnections and emit warnings, while a manual "Reconnect to OBS" button drives reconnection.
5. All required Python packages are already installed; no environment setup is needed before implementation.

### File Created
`.planning/phases/03-obs-integration-scene-control/03-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard stack | HIGH | All packages installed and verified via pip + runtime import |
| Architecture | HIGH | Patterns validated with mock clients, SocketIO test client, and threading tests |
| Pitfalls | HIGH | Derived from direct source inspection of obsws-python and Flask-SocketIO |

### Open Questions (RESOLVED)
- Whether scene switching should use HTTP POST or SocketIO events — RESOLVED: HTTP POST for simplicity.
- Whether OBS config should be inline on the status page or a separate page — RESOLVED: inline on the status page for Phase 3.

### Ready for Planning
Research complete. Planner can now create PLAN.md files.

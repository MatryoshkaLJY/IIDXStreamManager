# Phase 06: Score Review & Scoreboard Integration - Pattern Map

**Mapped:** 2026-04-15
**Files analyzed:** 8
**Analogs found:** 7 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/state.py` | model | CRUD | `src/state.py` (itself) | exact |
| `src/app.py` | controller | request-response | `src/app.py` (itself) | exact |
| `src/obs/monitor.py` | service | event-driven | `src/obs/monitor.py` (itself) | exact |
| `src/obs/scene_controller.py` | utility | request-response | `src/obs/scene_controller.py` (itself) | exact |
| `src/scoreboard/pusher.py` | service | request-response | `src/obs/client.py` | role-match |
| `src/templates/status.html` | component | request-response | `src/templates/status.html` (itself) | exact |
| `static/js/operator.js` | utility | event-driven | `static/js/operator.js` (itself) | exact |
| `static/css/main.css` | config | transform | `static/css/main.css` (itself) | exact |

## Pattern Assignments

### `src/state.py` (model, CRUD)

**Analog:** `src/state.py` (existing RuntimeState)

**Dataclass + default_factory pattern** (lines 1-30):
```python
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Optional

RUNTIME_STATE_PATH = Path("runtime/state.json")

@dataclass
class RuntimeState:
    config_paths: Dict[str, str] = field(default_factory=dict)
    loaded_at: Optional[str] = None
    obs_host: str = "localhost"
    obs_port: int = 4455
    obs_password: str = ""
    obs_connected: bool = False
    mode: str = ""
    current_round: int = 1
    cabinet_assignments: Dict[str, str] = field(default_factory=lambda: {"IIDX#1": "Unassigned", "IIDX#2": "Unassigned", "IIDX#3": "Unassigned", "IIDX#4": "Unassigned"})
    monitor_interval: float = 1.0
    monitoring_active: bool = False
    source_names: Dict[str, str] = field(default_factory=lambda: {
        "IIDX#1": "IIDX#1",
        "IIDX#2": "IIDX#2",
        "IIDX#3": "IIDX#3",
        "IIDX#4": "IIDX#4",
    })
    state_machine_config: str = "iidx_state_machine/state_machine.yaml"
```

**Save pattern** (lines 32-35):
```python
def save_runtime_state(state: RuntimeState, path: Path = RUNTIME_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(state), f, indent=2)
```

**Load with fallback defaults pattern** (lines 38-62):
```python
def load_runtime_state(path: Path = RUNTIME_STATE_PATH) -> RuntimeState:
    if not path.exists():
        return RuntimeState()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return RuntimeState(
        config_paths=data.get("config_paths", {}),
        loaded_at=data.get("loaded_at"),
        obs_host=data.get("obs_host", "localhost"),
        obs_port=data.get("obs_port", 4455),
        obs_password=data.get("obs_password", ""),
        obs_connected=data.get("obs_connected", False),
        mode=data.get("mode", ""),
        current_round=data.get("current_round", 1),
        cabinet_assignments=data.get("cabinet_assignments", {"IIDX#1": "Unassigned", "IIDX#2": "Unassigned", "IIDX#3": "Unassigned", "IIDX#4": "Unassigned"}),
        monitor_interval=data.get("monitor_interval", 1.0),
        monitoring_active=data.get("monitor_active", False),
        source_names=data.get("source_names", {
            "IIDX#1": "IIDX#1",
            "IIDX#2": "IIDX#2",
            "IIDX#3": "IIDX#3",
            "IIDX#4": "IIDX#4",
        }),
        state_machine_config=data.get("state_machine_config", "iidx_state_machine/state_machine.yaml"),
    )
```

---

### `src/app.py` (controller, request-response)

**Analog:** `src/app.py` (existing routes)

**Imports pattern** (lines 1-23):
```python
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_socketio import SocketIO
from pydantic import BaseModel, Field, field_validator

# Support direct execution: python src/app.py
if __package__ in (None, ""):
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.config.loader import ConfigError, get_player_names, load_configs
from src.obs import OBSClient, REQUIRED_SCENES, SceneController
from src.obs.heartbeat import OBSHeartbeat
from src.state import RUNTIME_STATE_PATH, RuntimeState, load_runtime_state, save_runtime_state
```

**Pydantic form validation pattern** (lines 25-48):
```python
class OBSConfigForm(BaseModel):
    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    password: str = ""

    @field_validator("host")
    @classmethod
    def host_must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("host must not be empty")
        return v.strip()
```

**POST route returning JSON pattern** (lines 112-121):
```python
@app.route("/switch_scene", methods=["POST"])
def switch_scene():
    data = request.get_json(silent=True) or request.form
    scene = (data.get("scene") or "").strip()
    if scene not in REQUIRED_SCENES.values():
        return jsonify({"success": False, "error": "Invalid scene name"}), 200
    ok, error = scene_controller.switch_to(scene)
    if ok:
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "error": error}), 200
```

**SocketIO emission from route pattern** (lines 282-309):
```python
@app.route("/save_round", methods=["POST"])
def save_round():
    payload = request.get_json(silent=True) or request.form.to_dict()
    try:
        form = RoundPrepForm(**payload)
    except Exception as exc:
        if request.is_json:
            return jsonify({"success": False, "error": str(exc)}), 200
        return redirect(url_for("round_prep"))

    runtime_state = load_runtime_state()
    runtime_state.cabinet_assignments = {
        "IIDX#1": form.cabinet_1,
        "IIDX#2": form.cabinet_2,
        "IIDX#3": form.cabinet_3,
        "IIDX#4": form.cabinet_4,
    }
    save_runtime_state(runtime_state)
    socketio.emit(
        "round_saved",
        {
            "round": runtime_state.current_round,
            "assignments": runtime_state.cabinet_assignments,
        },
    )
    if request.is_json:
        return jsonify({"success": True}), 200
    return redirect(url_for("round_prep"))
```

**SocketIO event handler pattern** (lines 331-339):
```python
@socketio.on("obs_reconnect")
def handle_obs_reconnect():
    if client.connected:
        client.disconnect()
    try:
        client.connect()
    except Exception:
        client.connected = False
    _validate_and_emit_obs_state()
```

**Background worker instantiation in create_app()** (lines 368-374, 376-382):
```python
    heartbeat = OBSHeartbeat(client, socketio, scene_controller=scene_controller, interval=3.0)
    heartbeat.start()

    monitor = CabinetMonitor(socketio, state_machine_config=runtime_state.state_machine_config)
    app._cabinet_monitor = monitor
```

---

### `src/obs/monitor.py` (service, event-driven)

**Analog:** `src/obs/monitor.py` (itself)

**Imports pattern** (lines 1-19):
```python
import json
import logging
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from flask_socketio import SocketIO

try:
    from obs_manager.obs_manager import OBSManager
except ImportError:
    project_root = str(Path(__file__).resolve().parents[3])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from obs_manager.obs_manager import OBSManager

from src.state import RuntimeState, load_runtime_state

logger = logging.getLogger(__name__)
```

**Daemon thread lifecycle pattern** (lines 27-53):
```python
class CabinetMonitor:
    def __init__(self, socketio: SocketIO, state_machine_config: str = "iidx_state_machine/state_machine.yaml") -> None:
        self.socketio = socketio
        self.state_machine_config = state_machine_config
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._obs_manager: Optional[OBSManager] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
```

**SocketIO emit from background thread pattern** (lines 128-139):
```python
                payload: Dict[str, Any] = {
                    "machine_id": result.get("machine_id", machine_id),
                    "label": result.get("label"),
                    "state": result.get("state"),
                    "scores": result.get("scores"),
                    "score_validation_pending": result.get("score_validation_pending", False),
                }
                print(json.dumps(payload, ensure_ascii=False, default=str))
                self.socketio.emit("cabinet_update", payload)
```

---

### `src/obs/scene_controller.py` (utility, request-response)

**Analog:** `src/obs/scene_controller.py` (itself)

**Scene switching pattern** (lines 43-54):
```python
    def switch_to(self, scene_name: str) -> Tuple[bool, str]:
        if not self.obs.connected or not self.scenes_valid:
            return False, "OBS not ready"

        if scene_name not in REQUIRED_SCENES.values():
            return False, "Unknown scene"

        try:
            self.obs.set_current_program_scene(scene_name)
            return True, ""
        except OBSSDKRequestError as e:
            return False, str(e)
```

**Extending REQUIRED_SCENES pattern** (lines 8-13):
```python
REQUIRED_SCENES = {
    "live": "现场摄像",
    "sp_team": "SP团队赛",
    "dp_team": "DP团队赛",
    "individual": "个人赛",
}
```

---

### `src/scoreboard/pusher.py` (service, request-response)

**Analog:** `src/obs/client.py`

**Imports pattern** (lines 1-5):
```python
from typing import Any, Dict, Optional

import obsws_python
from obsws_python.error import OBSSDKError
```

**Wrapper class pattern** (lines 7-68):
```python
class OBSClient:
    def __init__(self, host: str = "localhost", port: int = 4455, password: str = "") -> None:
        self.host = host
        self.port = port
        self.password = password
        self._client: Optional[obsws_python.ReqClient] = None

    def connect(self) -> None:
        self._client = obsws_python.ReqClient(...)

    def disconnect(self) -> None:
        if self._client is not None:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None

    @property
    def connected(self) -> bool:
        ...
```

**Error handling pattern** (lines 29-35):
```python
    def disconnect(self) -> None:
        if self._client is not None:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
```

---

### `src/templates/status.html` (component, request-response)

**Analog:** `src/templates/status.html` (itself)

**Conditional banner pattern** (lines 4-14):
```html
<div id="obs-banner" class="card" style="display: {% if not obs_connected or missing_scenes %}block{% else %}none{% endif %};">
  <p id="obs-banner-text" class="status-error">
    {% if not obs_connected %}
      OBS disconnected. Scene switching and auto-transitions are paused.
      <button id="obs-reconnect-btn" type="button">Reconnect to OBS</button>
    {% elif missing_scenes %}
      OBS scenes missing: {{ missing_scenes | join(", ") }}. Please add them in OBS, then click Retry Validation.
      <button id="obs-reconnect-btn" type="button">Retry Validation</button>
    {% endif %}
  </p>
</div>
```

**Form + button row pattern** (lines 78-88):
```html
<div class="card">
  <h2 class="heading">Scene Switching</h2>
  <div class="button-row">
    {% for scene in ["现场摄像", "SP团队赛", "DP团队赛", "个人赛"] %}
      <form method="post" action="{{ url_for('switch_scene') }}" class="scene-form">
        <input type="hidden" name="scene" value="{{ scene }}">
        <button type="submit" class="scene-btn" {% if not obs_connected or not scenes_valid %}disabled{% endif %}>{{ scene }}</button>
      </form>
    {% endfor %}
  </div>
</div>
```

**SocketIO JS include pattern** (lines 91-94):
```html
{% block extra_js %}
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<script src="{{ url_for('static', filename='js/operator.js') }}"></script>
{% endblock %}
```

---

### `static/js/operator.js` (utility, event-driven)

**Analog:** `static/js/operator.js` (itself)

**Socket connection + event handler pattern** (lines 1-14):
```javascript
(function () {
  const socket = io();

  const banner = document.getElementById('obs-banner');
  const bannerText = document.getElementById('obs-banner-text');
  const statusLabel = document.getElementById('obs-status-label');
  const sceneButtons = document.querySelectorAll('.scene-btn');
  const configForm = document.getElementById('obs-config-form');
```

**SocketIO event consumption pattern** (lines 45-82):
```javascript
  socket.on('obs_status', (data) => {
    const connected = !!data.connected;
    const scenesValid = !!data.scenes_valid;

    if (connected && scenesValid) {
      if (banner) banner.style.display = 'none';
      if (statusLabel) {
        statusLabel.textContent = 'OBS: Connected';
        statusLabel.className = 'status-ok';
      }
      setSceneButtonsDisabled(false);
    } else if (connected && !scenesValid) {
      // ...
    } else {
      // ...
    }
  });
```

**Emit event on button click pattern** (lines 84-93):
```javascript
  if (banner) {
    banner.addEventListener('click', (event) => {
      if (event.target && event.target.tagName === 'BUTTON') {
        const label = event.target.textContent || '';
        if (label === 'Reconnect to OBS' || label === 'Retry Validation') {
          socket.emit('obs_reconnect');
        }
      }
    });
  }
```

**Fetch POST from form submit pattern** (lines 104-127):
```javascript
  if (configForm) {
    configForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const formData = new FormData(configForm);
      const payload = {
        host: formData.get('host') || '',
        port: parseInt(formData.get('port') || '0', 10),
        password: formData.get('password') || '',
      };
      fetch(configForm.action, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
        .then((resp) => {
          if (!resp.ok) {
            console.error('OBS config save failed', resp.status);
          }
        })
        .catch((err) => {
          console.error('OBS config save error', err);
        });
    });
  }
```

---

### `static/css/main.css` (config, transform)

**Analog:** `static/css/main.css` (itself)

**Color variable pattern** (lines 1-9):
```css
:root {
  --color-dominant: #0f172a;
  --color-secondary: #1e293b;
  --color-accent: #22c55e;
  --color-destructive: #ef4444;
  --color-warning: #f59e0b;
  --color-text-primary: #f8fafc;
  --color-text-secondary: #94a3b8;
```

**Card and button pattern** (lines 27-31, 94-117):
```css
.card {
  background: var(--color-secondary);
  border-radius: 8px;
  padding: var(--space-md);
  margin-bottom: var(--space-md);
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}
.scene-btn {
  padding: var(--space-sm) var(--space-md);
  background: var(--color-secondary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-text-secondary);
  border-radius: 4px;
  cursor: pointer;
}
.scene-btn:hover:not(:disabled) {
  background: var(--color-accent);
  border-color: var(--color-accent);
}
.scene-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

**Status text pattern** (lines 54-64):
```css
.status-ok {
  color: var(--color-accent);
}
.status-error {
  color: var(--color-destructive);
}
.status-warning {
  color: var(--color-warning);
}
```

## Shared Patterns

### Authentication
None — this project has no auth layer.

### Error Handling (graceful degradation)
**Source:** `src/app.py` lines 141-144 and `src/obs/heartbeat.py` lines 42-49
**Apply to:** All service and controller files
```python
try:
    client.connect()
except Exception:
    client.connected = False
```

### SocketIO Broadcast from Background Thread
**Source:** `src/obs/monitor.py` lines 128-139
**Apply to:** `src/app.py`, `src/obs/monitor.py`
```python
self.socketio.emit("cabinet_update", payload)
```

### RuntimeState Extension
**Source:** `src/state.py`
**Apply to:** `src/state.py`
Add new fields with defaults to the `@dataclass` and to `load_runtime_state()` `.get()` fallbacks.

### Template Conditional Rendering
**Source:** `src/templates/status.html` lines 4-14
**Apply to:** `src/templates/status.html`
Use `{% if monitoring_active %}...{% else %}...{% endif %}` to show/hide monitor controls and banners.

### Fetch POST with JSON from Vanilla JS
**Source:** `static/js/operator.js` lines 104-127
**Apply to:** `static/js/operator.js`
```javascript
fetch(form.action, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
})
```

### SceneController.switch_to() Usage
**Source:** `src/obs/scene_controller.py` lines 43-54
**Apply to:** `src/app.py`
```python
ok, error = scene_controller.switch_to(scene_name)
if ok:
    return jsonify({"success": True}), 200
return jsonify({"success": False, "error": error}), 200
```

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/scoreboard/pusher.py` | service | request-response | No WebSocket client wrapper for scoreboards exists yet; closest analog is `src/obs/client.py` (role-match) |

## Metadata

**Analog search scope:** `src/`, `static/`, `../obs_manager/`
**Files scanned:** 18
**Pattern extraction date:** 2026-04-15

# Phase 04: Tournament Setup & Round Prep UI - Pattern Map

**Mapped:** 2026-04-15
**Files analyzed:** 7
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/app.py` | controller | request-response | `src/app.py` (existing) | exact |
| `src/state.py` | model | file-I/O | `src/state.py` (existing) | exact |
| `src/config/loader.py` | utility | file-I/O | `src/config/loader.py` (existing) | exact |
| `src/config/models.py` | model | transform | `src/config/models.py` (existing) | exact |
| `src/templates/base.html` | component | request-response | `src/templates/base.html` (existing) | exact |
| `src/templates/status.html` | component | request-response | `src/templates/status.html` (existing) | exact |
| `static/css/main.css` | config | file-I/O | `static/css/main.css` (existing) | exact |

## Pattern Assignments

### `src/app.py` (controller, request-response)

**Analog:** `src/app.py`

**Imports pattern** (lines 1-20):
```python
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO
from pydantic import BaseModel, Field, field_validator

# Support direct execution: python src/app.py
if __package__ in (None, ""):
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.config.loader import ConfigError, load_configs
from src.obs import OBSClient, REQUIRED_SCENES, SceneController
from src.obs.heartbeat import OBSHeartbeat
from src.state import RUNTIME_STATE_PATH, RuntimeState, load_runtime_state, save_runtime_state
```

**Pydantic form validation pattern** (lines 22-33):
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

**Flask app factory pattern** (lines 35-41):
```python
def create_app(return_socketio: bool = False):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

    socketio = SocketIO(app, cors_allowed_origins="*")

    runtime_state = load_runtime_state()
```

**Route returning JSON for POST handlers** (lines 83-92):
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

**POST route with Pydantic validation + state persistence** (lines 94-126):
```python
@app.route("/obs_config", methods=["POST"])
def obs_config():
    payload = request.get_json(silent=True) or request.form.to_dict()
    try:
        form = OBSConfigForm(**payload)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 200

    runtime_state = load_runtime_state()
    runtime_state.obs_host = form.host
    runtime_state.obs_port = form.port
    runtime_state.obs_password = form.password
    save_runtime_state(runtime_state)
    ...
    return jsonify({"success": True, ...}), 200
```

**Eager config load inside app context** (lines 138-156):
```python
with app.app_context():
    try:
        loaded = load_configs()
        from src.config.loader import CONFIG_FILES
        config_paths = {
            key: str(Path("data") / filename)
            for key, (filename, _) in CONFIG_FILES.items()
        }
        runtime_state = load_runtime_state()
        runtime_state.config_paths = config_paths
        runtime_state.loaded_at = datetime.now(timezone.utc).isoformat()
        save_runtime_state(runtime_state)
    except ConfigError as exc:
        app.config["CONFIG_ERROR"] = str(exc)
```

**Template render with state and error injection** (lines 66-82):
```python
@app.route("/")
def status():
    runtime_state = load_runtime_state()
    return render_template(
        "status.html",
        server_port=5002,
        state_path=str(RUNTIME_STATE_PATH),
        config_error=app.config.get("CONFIG_ERROR"),
        runtime_state=runtime_state,
        obs_connected=client.connected,
        scenes_valid=scene_controller.scenes_valid,
        missing_scenes=scene_controller.missing_scenes,
        obs_host=runtime_state.obs_host,
        obs_port=runtime_state.obs_port,
        obs_password=runtime_state.obs_password,
    )
```

---

### `src/state.py` (model, file-I/O)

**Analog:** `src/state.py`

**Dataclass state model pattern** (lines 1-18):
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
```

**Save pattern** (lines 20-23):
```python
def save_runtime_state(state: RuntimeState, path: Path = RUNTIME_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(state), f, indent=2)
```

**Load pattern with `.get()` fallbacks** (lines 26-38):
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
    )
```

---

### `src/config/loader.py` (utility, file-I/O)

**Analog:** `src/config/loader.py`

**ConfigError exception pattern** (lines 14-18):
```python
class ConfigError(Exception):
    """Raised when a config file cannot be loaded or validated."""
    pass
```

**CONFIG_FILES registry pattern** (lines 20-25):
```python
CONFIG_DIR = Path("data")
CONFIG_FILES: Dict[str, tuple[str, Any]] = {
    "teams": ("teams.json", TeamsConfig),
    "team_schedule": ("team_schedule.json", TeamScheduleConfig),
    "individual_schedule": ("individual_schedule.json", IndividualScheduleConfig),
}
```

**Template generation pattern** (lines 27-42):
```python
TEMPLATES: Dict[str, dict] = {
    "teams.json": {"teams": []},
    "team_schedule.json": {"weeks": []},
    "individual_schedule.json": {"groups": {}},
}

def ensure_templates(config_dir: Path = CONFIG_DIR) -> None:
    """Generate minimal valid templates for missing config files."""
    config_dir.mkdir(parents=True, exist_ok=True)
    for key, (filename, _) in CONFIG_FILES.items():
        path = config_dir / filename
        if not path.exists():
            template = TEMPLATES[filename]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=2)
```

**Load + validate pattern with Pydantic** (lines 45-69):
```python
def load_configs(config_dir: Path = CONFIG_DIR) -> Dict[str, Any]:
    """Load and validate all config files, generating templates if missing."""
    ensure_templates(config_dir)
    loaded: Dict[str, Any] = {}
    for key, (filename, model_cls) in CONFIG_FILES.items():
        path = config_dir / filename
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"Config error: {path.name} is not valid JSON. "
                "Fix the file and reload the page to retry."
            ) from exc
        try:
            loaded[key] = model_cls.model_validate(raw)
        except ValidationError as exc:
            first_error = exc.errors()[0]
            loc = ".".join(str(part) for part in first_error.get("loc", []))
            err_msg = f"{loc}: {first_error.get('msg', 'validation error')}"
            raise ConfigError(
                f"Config error: {path.name} — {err_msg}. "
                "Fix the file and reload the page to retry."
            ) from exc
    return loaded
```

---

### `src/config/models.py` (model, transform)

**Analog:** `src/config/models.py`

**Pydantic model pattern** (lines 1-66):
```python
from typing import Dict, List, Literal

from pydantic import BaseModel

class Player(BaseModel):
    id: str
    name: str
    role: str

class TeamColors(BaseModel):
    primary: str
    secondary: str
    accent: str

class Team(BaseModel):
    id: str
    name: str
    emoji: str
    colors: TeamColors
    players: List[Player]

class TeamsConfig(BaseModel):
    teams: List[Team]

class Round(BaseModel):
    type: Literal["1v1", "2v2"]
    theme: str
    left_players: List[str]
    right_players: List[str]

class Match(BaseModel):
    left_team: str
    right_team: str
    template: str
    rounds: List[Round]

class Week(BaseModel):
    matches: List[Match]

class TeamScheduleConfig(BaseModel):
    weeks: List[Week]

class IndividualScheduleConfig(BaseModel):
    groups: Dict[str, List[str]]

__all__ = [
    "Player",
    "TeamColors",
    "Team",
    "TeamsConfig",
    "Round",
    "Match",
    "Week",
    "TeamScheduleConfig",
    "IndividualScheduleConfig",
]
```

---

### `src/templates/base.html` (component, request-response)

**Analog:** `src/templates/base.html`

**Jinja2 base template pattern** (lines 1-16):
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{% block title %}IIDX Tournament Auto-Director{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
</head>
<body>
  <nav class="card">
    <a href="{{ url_for('status') }}">Status</a>
    <a href="#">Config</a>
  </nav>
  {% block content %}{% endblock %}
  {% block extra_js %}{% endblock %}
</body>
</html>
```

---

### `src/templates/status.html` (component, request-response)

**Analog:** `src/templates/status.html`

**Conditional error banner pattern** (lines 4-14):
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

**Conditional status text pattern** (lines 16-18):
```html
<p id="obs-status-label" class="{% if obs_connected and not missing_scenes %}status-ok{% else %}status-error{% endif %}">
  OBS: {% if obs_connected and not missing_scenes %}Connected{% else %}Disconnected{% endif %}
</p>
```

**Config error display pattern** (lines 28-32):
```html
{% if config_error %}
  <p class="status-error">{{ config_error }}</p>
  <p class="label">No config loaded</p>
  <p>Place teams.json, team_schedule.json, and individual_schedule.json in the data/ folder, then restart the application.</p>
{% else %}
  <p class="status-ok">All configs loaded successfully.</p>
  ...
{% endif %}
```

**Form row pattern** (lines 47-63):
```html
<form id="obs-config-form" method="post" action="{{ url_for('obs_config') }}">
  <div class="form-row">
    <label class="label" for="obs-host">Host</label>
    <input type="text" id="obs-host" name="host" value="{{ runtime_state.obs_host }}" required>
    <span class="hint">Use localhost or 127.0.0.1 for local OBS</span>
  </div>
  ...
  <button type="submit" {% if not obs_connected and missing_scenes %}disabled{% endif %}>Save & Reconnect</button>
</form>
```

**Button row pattern** (lines 67-75):
```html
<div class="button-row">
  {% for scene in ["现场摄像", "SP团队赛", "DP团队赛", "个人赛"] %}
    <form method="post" action="{{ url_for('switch_scene') }}" class="scene-form">
      <input type="hidden" name="scene" value="{{ scene }}">
      <button type="submit" class="scene-btn" {% if not obs_connected or not scenes_valid %}disabled{% endif %}>{{ scene }}</button>
    </form>
  {% endfor %}
</div>
```

**SocketIO JS include pattern** (lines 78-81):
```html
{% block extra_js %}
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<script src="{{ url_for('static', filename='js/operator.js') }}"></script>
{% endblock %}
```

---

### `static/css/main.css` (config, file-I/O)

**Analog:** `static/css/main.css`

**CSS token pattern** (lines 1-15):
```css
:root {
  --color-dominant: #0f172a;
  --color-secondary: #1e293b;
  --color-accent: #22c55e;
  --color-destructive: #ef4444;
  --color-warning: #f59e0b;
  --color-text-primary: #f8fafc;
  --color-text-secondary: #94a3b8;
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
}
```

**Card, label, heading, display patterns** (lines 27-52):
```css
.card {
  background: var(--color-secondary);
  border-radius: 8px;
  padding: var(--space-md);
  margin-bottom: var(--space-md);
}

.label {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--color-text-secondary);
}

.heading {
  font-size: 20px;
  font-weight: 600;
  line-height: 1.2;
  margin: 0 0 var(--space-sm) 0;
}

.display {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.15;
}
```

**Status color classes** (lines 54-64):
```css
.status-ok { color: var(--color-accent); }
.status-error { color: var(--color-destructive); }
.status-warning { color: var(--color-warning); }
```

**Form row pattern** (lines 79-92):
```css
.form-row {
  margin-bottom: var(--space-sm);
}
.form-row input {
  display: block;
  width: 100%;
  max-width: 300px;
  padding: var(--space-sm);
  background: var(--color-dominant);
  color: var(--color-text-primary);
  border: 1px solid var(--color-text-secondary);
  border-radius: 4px;
  font-size: 16px;
}
```

**Button row pattern** (lines 94-99):
```css
.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}
```

**Nav link pattern** (lines 128-136):
```css
nav a {
  color: var(--color-text-secondary);
  text-decoration: none;
  margin-right: var(--space-md);
}

nav a:hover {
  color: var(--color-text-primary);
}
```

---

## Shared Patterns

### Pydantic Form Validation
**Source:** `src/app.py` lines 22-33
**Apply to:** New POST routes in `src/app.py` (config upload, round prep, mode selection)
```python
class SomeForm(BaseModel):
    field: str = Field(..., min_length=1)

    @field_validator("field")
    @classmethod
    def validate_field(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v.strip()
```

### JSON POST Handler with Fallback to Form
**Source:** `src/app.py` lines 85-86, 96-100
**Apply to:** All new POST routes in `src/app.py`
```python
data = request.get_json(silent=True) or request.form
# or
payload = request.get_json(silent=True) or request.form.to_dict()
try:
    form = SomeForm(**payload)
except Exception as exc:
    return jsonify({"success": False, "error": str(exc)}), 200
```

### RuntimeState Persistence
**Source:** `src/state.py`
**Apply to:** Any new state fields (`mode`, `current_round`, `cabinet_assignments`)
- Add field to `RuntimeState` dataclass with a sensible default
- Add corresponding `.get(..., default)` in `load_runtime_state()`
- `save_runtime_state()` works automatically via `asdict(state)`

### Config Loading and Error Banner
**Source:** `src/app.py` lines 138-156, `src/templates/status.html` lines 28-32
**Apply to:** Config upload validation flow
- Call validation logic inside `app.app_context()` or route handler
- On `ConfigError`, store `app.config["CONFIG_ERROR"] = str(exc)`
- Render `config_error` in templates as `<p class="status-error">{{ config_error }}</p>`

### Jinja2 Template Extension
**Source:** `src/templates/status.html` lines 1-2
**Apply to:** New pages (`config.html`, `round_prep.html`)
```html
{% extends "base.html" %}
{% block title %}Page Title{% endblock %}
{% block content %}
  ...
{% endblock %}
```

### SocketIO Event Emission
**Source:** `src/app.py` lines 57-64
**Apply to:** Real-time UI updates after state changes
```python
socketio.emit("event_name", {"key": value})
```

### File Backup Before Overwrite
**Source:** None in codebase — use standard library
**Apply to:** Config upload in `src/app.py`
```python
import shutil
from datetime import datetime

if target_path.exists():
    backup_path = target_path.with_suffix(f"{target_path.suffix}.bak")
    shutil.copy2(target_path, backup_path)
```

## No Analog Found

None — all target files have exact existing analogs in the codebase.

## Metadata

**Analog search scope:** `src/`, `src/templates/`, `static/css/`, `src/config/`
**Files scanned:** 11
**Pattern extraction date:** 2026-04-15

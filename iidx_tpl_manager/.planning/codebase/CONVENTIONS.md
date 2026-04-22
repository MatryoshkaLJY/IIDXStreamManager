# Coding Conventions

**Analysis Date:** 2026-04-22

## Naming Patterns

**Files:**
- Source modules use `snake_case.py`: `scene_controller.py`, `auto_transition.py`, `config_loader.py`
- Test files use `test_<module_name>.py`: `test_scene_controller.py`, `test_config_loader.py`
- Package `__init__.py` files act as barrel files exposing public API

**Classes:**
- PascalCase for all classes: `RuntimeState`, `OBSClient`, `SceneController`, `AutoTransitionController`, `CabinetMonitor`, `ScoreboardPusher`, `OBSHeartbeat`
- Pydantic models also use PascalCase: `TeamsConfig`, `TeamScheduleConfig`, `IndividualScheduleConfig`, `Round`, `Match`, `Week`, `Player`, `TeamColors`

**Functions/Methods:**
- snake_case everywhere: `load_runtime_state`, `save_runtime_state`, `validate_scenes`, `switch_to`, `push_team_score`
- Private methods use single underscore prefix: `_run`, `_tick`, `_check_prerequisites`, `_set_automation_state`, `_resolve_gameplay_scene`, `_ensure_obs_manager`, `_send_async`
- Boolean-returning methods often use `is_` or past-participle naming: `connected` (property)

**Variables:**
- snake_case for local variables: `runtime_state`, `scene_controller`, `pending_scores`
- Module-level constants use UPPER_SNAKE_CASE: `RUNTIME_STATE_PATH`, `REQUIRED_SCENES`, `CONFIG_FILES`, `BPL_URI`, `KNOCKOUT_URI`, `DEFAULT_MACHINES`, `DEFAULT_STATE_MACHINE_CONFIG`
- Private instance variables use single underscore prefix: `_client`, `_thread`, `_stop`, `_obs_manager`, `_machine_states`, `_gameplay_entered_at`, `_pending_transition`, `_paused_reason`

**Types:**
- Type hints use `typing` module imports: `Dict`, `List`, `Optional`, `Tuple`, `Any`
- Union syntax uses `|` operator (Python 3.10+): `threading.Thread | None`
- Pydantic form classes use `Form` suffix: `OBSConfigForm`, `ModeForm`, `RoundPrepForm`, `ScoreboardDelayForm`, `AutomationDelaysForm`

## Code Style

**Formatting:**
- No explicit formatter config detected (no `.prettierrc`, `ruff.toml`, `.flake8`, etc.)
- Code appears to follow PEP 8 by convention
- Line length appears to be ~100-120 characters in practice
- Double quotes for strings consistently used

**Linting:**
- No linting config files detected
- No `pyproject.toml`, `setup.cfg`, or `tox.ini` found
- Project appears to rely on manual style discipline

## Import Organization

**Order (observed pattern):**
1. Standard library: `import json`, `import os`, `import sys`, `import threading`, `from pathlib import Path`
2. Third-party libraries: `from flask import ...`, `from flask_socketio import SocketIO`, `from pydantic import ...`, `import obsws_python`, `import websockets`
3. Local modules: `from src.config.loader import ...`, `from src.obs.client import ...`, `from src.state import ...`

**Path Hacks:**
- Several modules include runtime `sys.path` manipulation for sibling-directory imports (`obs_manager`):
  - `src/obs/monitor.py` lines 10-17
  - `src/app.py` lines 14-17 (for direct execution support)
- This is a known architectural smell — the project depends on `obs_manager` living in a sibling directory to the project root

**Path Aliases:**
- No import aliases used
- Absolute imports from `src.` package root preferred over relative imports

## Error Handling

**Patterns:**
- Custom exception class for domain errors: `ConfigError(Exception)` in `src/config/loader.py`
- Specific exception catching preferred over bare `except`:
  - `except json.JSONDecodeError as exc:`
  - `except ValidationError as exc:`
  - `except OBSSDKRequestError as e:`
- However, broad `except Exception` is used in several places for resilience:
  - `src/obs/client.py` lines 31-34 (disconnect cleanup)
  - `src/obs/heartbeat.py` lines 44-49 (heartbeat resilience)
  - `src/obs/monitor.py` lines 75-76, 85-91, 160-162 (monitor resilience)

**Error Propagation in Flask Routes:**
- Routes catch exceptions and return JSON with `"success": False`:
  ```python
  try:
      form = OBSConfigForm(**payload)
  except Exception as exc:
      return jsonify({"success": False, "error": str(exc)}), 200
  ```
- HTTP 200 used even for errors (API convention, not RESTful status codes)

## Type Hint Usage

**Coverage:**
- All function signatures have type hints in production code
- Return types explicitly annotated: `-> None`, `-> bool`, `-> Tuple[bool, str]`, `-> Dict[str, Any]`
- Pydantic models provide runtime validation alongside static types

**Notable Patterns:**
- `TYPE_CHECKING` guard for circular imports: `src/obs/scene_controller.py` imports `OBSClient` only under `TYPE_CHECKING`
- `Any` used pragmatically for OBS SDK return types and JSON payloads
- Union types use `|` syntax: `threading.Thread | None`

## Docstring Style

**Format:**
- Google-style docstrings (short description + optional detail)
- Example from `src/obs/client.py`:
  ```python
  class OBSClient:
      """Lazy-connect OBS WebSocket v5 client wrapper."""
  ```
- Example from `src/obs/heartbeat.py`:
  ```python
  class OBSHeartbeat:
      """Background heartbeat that monitors OBS connection health.

      Emits obs_status events at a fixed interval. Does NOT auto-reconnect.
      """
  ```
- Not all classes/methods have docstrings (e.g., `RuntimeState` dataclass has none)
- Test methods use descriptive names instead of docstrings

## Configuration Patterns

**Pydantic Models for Validation:**
- All JSON configs validated via Pydantic `BaseModel` subclasses in `src/config/models.py`
- `Literal` types used for enum-like fields: `type: Literal["1v1", "2v2"]`
- Default values in models: `points: int = 1`

**Runtime State:**
- `RuntimeState` is a plain `@dataclass` (not frozen), mutable across the application
- Persisted to JSON via `dataclasses.asdict` in `src/state.py`
- Default values embedded in the dataclass definition
- Backward compatibility handled manually in `load_runtime_state()` with `.get(..., default)` for every field

**Flask App Factory:**
- `create_app(return_socketio: bool = False)` factory pattern in `src/app.py`
- Configuration forms are Pydantic models, not WTForms

## Design Patterns

**No Factory/Registry Patterns:**
- Despite the user's global coding-style rule requiring Factory & Registry patterns, this codebase does NOT use them
- No `__init__.py` registry dictionaries
- No `@register_*` decorators
- Classes are instantiated directly

**Wrapper/Facade Pattern:**
- `OBSClient` wraps `obsws_python.ReqClient` with lazy connection and state management
- `SceneController` wraps `OBSClient` with scene validation and switching logic

**Background Worker Pattern:**
- Three daemon thread workers share a common structure:
  - `OBSHeartbeat` (`src/obs/heartbeat.py`)
  - `CabinetMonitor` (`src/obs/monitor.py`)
  - `AutoTransitionController` (`src/obs/auto_transition.py`)
- Common interface: `start()`, `stop()`, `_run()` with `threading.Event` for cancellation

**State Machine (External):**
- `CabinetMonitor` delegates to external `OBSManager` from sibling `obs_manager` package
- `obs.init_state_machine()` called with YAML config path

## Deviations from PEP 8 / User's Global Rules

1. **File Size:** `src/app.py` is 676 lines — exceeds the user's 400-line limit from `coding-style.md`
2. **No Factory/Registry:** User's global rule requires Factory & Registry patterns for all modules; this codebase instantiates classes directly
3. **Mutable Dataclass:** `RuntimeState` is mutable (`@dataclass` without `frozen=True`), violating the user's "Immutability First" rule
4. **No `__all__` in all packages:** Only `src/config/__init__.py` and `src/scoreboard/__init__.py` define `__all__`; `src/obs/__init__.py` does but `src/state.py` does not
5. **Broad Exception Catching:** Multiple `except Exception` blocks used for resilience, though user's rules discourage bare except
6. **No Formal Linting/Type Checking:** No `mypy`, `ruff`, or `pytest` config files detected; no CI enforcement
7. **Path Manipulation at Runtime:** `sys.path.insert()` hacks in production code for sibling-directory imports

## Comments

**Inline Comments:**
- Sparse but purposeful; often reference design decision IDs (e.g., `# D-01:`, `# D-02:`, `# D-07:`, `# D-15:`, `# D-16:`)
- These appear to be requirement/phase identifiers from the planning process

**TODO/FIXME:**
- No TODO, FIXME, HACK, or XXX comments found in source code

---

*Convention analysis: 2026-04-22*

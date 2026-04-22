# Codebase Concerns

**Analysis Date:** 2026-04-22

## Tech Debt

### Monolithic app.py (676 lines)
- **Issue:** `src/app.py` is 676 lines, mixing route handlers, form validation, business logic (score computation, schedule flattening), and template rendering.
- **Files:** `src/app.py`
- **Impact:** Difficult to test individual behaviors; changes to one route risk breaking others; violates the 200-400 line file guideline from `coding-style.md`.
- **Fix approach:** Extract score-computation logic into `src/scoreboard/compute.py`, extract template-context building into a helper, and keep routes thin.

### Duplicated Template Context Building
- **Issue:** The same 4 automation parameters (`automation_active`, `automation_state`, `return_to_live_delay`, `gameplay_hold_delay`) are passed explicitly to `render_template` in 4 routes (`status`, `config`, `round_prep`, `automation`).
- **Files:** `src/app.py` lines 126-129, 349-352, 461-464, 609-612
- **Impact:** Adding a new shared context variable requires edits in 4 places; easy to miss one.
- **Fix approach:** Introduce a `_build_common_context(runtime_state)` helper that returns the shared dict.

### Duplicated Player-Name Loading
- **Issue:** The pattern `load_configs() -> get_player_names() -> catch ConfigError -> pass` is repeated in `config()`, `round_prep()`, and inside `create_app()`.
- **Files:** `src/app.py` lines 336-343, 448-455, 528-545
- **Impact:** Inconsistent error handling; `CONFIG_ERROR` logic scattered.
- **Fix approach:** Extract a single `get_player_names_safe()` helper.

### Inline Schedule Flattening in confirm_score
- **Issue:** `confirm_score()` contains a triple-nested loop (`week -> match -> round`) with a manual counter to map `current_round` to a schedule entry. This is business logic embedded directly in a route handler.
- **Files:** `src/app.py` lines 193-206
- **Impact:** Hard to unit test; fragile if schedule structure changes.
- **Fix approach:** Extract a `find_round_by_number(schedule, round_number)` utility in `src/config/loader.py`.

### Hardcoded DP/SP Scene Selection Stub
- **Issue:** `_resolve_gameplay_scene()` in `AutoTransitionController` always returns `REQUIRED_SCENES["sp_team"]` for team mode, with a comment "For now, default to SP团队赛".
- **Files:** `src/obs/auto_transition.py` lines 172-175
- **Impact:** DP team matches will incorrectly transition to the SP team scene.
- **Fix approach:** Read the current round's `type` / `theme` from the loaded schedule config to determine SP vs DP.

## Known Bugs

### RuntimeState Missing `missing_scenes` Field
- **Issue:** `src/app.py` line 97 assigns `runtime_state.missing_scenes = scene_controller.missing_scenes`, but the `RuntimeState` dataclass in `src/state.py` does not declare a `missing_scenes` field. In Python 3.13 this raises `AttributeError` on the assignment.
- **Files:** `src/app.py:97`, `src/state.py:10-36`
- **Trigger:** Call `_validate_and_emit_obs_state()` when OBS is connected.
- **Workaround:** None; the code will crash.
- **Fix approach:** Add `missing_scenes: List[str] = field(default_factory=list)` to `RuntimeState` and include it in `load_runtime_state()`.

### Unused `scoreboard_delay` Config
- **Issue:** `scoreboard_delay` is stored in `RuntimeState`, exposed in the UI, and has an API endpoint (`/api/scoreboard_delay`), but it is never read by `ScoreboardPusher` or anywhere else in the score-pushing flow.
- **Files:** `src/state.py:30`, `src/app.py:143-154`, `src/scoreboard/pusher.py`
- **Trigger:** Operator sets a scoreboard delay expecting a timed push; push happens immediately instead.
- **Fix approach:** Either wire `scoreboard_delay` into `confirm_score()` (e.g., `time.sleep` or threaded delay before calling `pusher.push_*`), or remove the field and UI to avoid confusion.

### File Upload Stream Double-Read Risk
- **Issue:** In `upload_config()`, `json.load(file.stream)` is called first for validation, then `file.stream.seek(0)` is attempted, followed by `file.read()`. If the uploaded `FileStorage` wrapper does not support `seek()` (some WSGI environments), the second read may return empty bytes and write an empty file.
- **Files:** `src/app.py` lines 409, 420-422
- **Impact:** Valid config file could be overwritten with empty content after passing validation.
- **Fix approach:** Read bytes once into memory, validate from the bytes, then write the same bytes.

## Security Considerations

### Hardcoded Flask SECRET_KEY Fallback
- **Issue:** `app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")` uses a predictable default.
- **Files:** `src/app.py:76`
- **Risk:** Session cookies can be forged if the app is run without setting the env var.
- **Current mitigation:** None in production; relies on operator to set env var.
- **Recommendations:** Fail hard on startup if `SECRET_KEY` is not set in production, or generate a random key and warn.

### CORS Allowed Origins Set to "*"
- **Issue:** `SocketIO(app, cors_allowed_origins="*")` allows any origin to connect.
- **Files:** `src/app.py:78`
- **Risk:** Cross-origin WebSocket connections from malicious sites could interact with the control panel.
- **Current mitigation:** App runs on local network; but still exposed via `0.0.0.0`.
- **Recommendations:** Restrict to `localhost:5002` or the known streaming-PC IP.

### OBS Password Rendered in HTML Template
- **Issue:** The OBS WebSocket password is passed to the template and rendered as the `value` of a password input field (`value="{{ runtime_state.obs_password }}"`).
- **Files:** `src/templates/status.html:59`
- **Risk:** Password is visible in page source; anyone with UI access can read it.
- **Current mitigation:** None.
- **Recommendations:** Do not pre-fill the password field; leave it empty and require re-entry on config change.

### `allow_unsafe_werkzeug=True` in Production Run Block
- **Issue:** `socketio.run(app, host="0.0.0.0", port=5002, allow_unsafe_werkzeug=True)` disables a Werkzeug security warning.
- **Files:** `src/app.py:676`
- **Risk:** Signals that the dev server may be used in production; Werkzeug is not a production WSGI server.
- **Recommendations:** Document that this block is for development only; production should use gunicorn + eventlet as noted in `CLAUDE.md`.

## Performance Bottlenecks

### Synchronous Scoreboard Push Blocks Request
- **Issue:** `ScoreboardPusher._send()` calls `asyncio.run(self._send_async(...))` inside a synchronous Flask route handler. This blocks the request thread until the WebSocket connection completes.
- **Files:** `src/scoreboard/pusher.py:49-55`
- **Problem:** If the scoreboard server is slow or unreachable, the `confirm_score` HTTP request hangs.
- **Improvement path:** Use `socketio.start_background_task` or a dedicated thread pool to push scores asynchronously, returning success immediately and emitting a failure event if needed.

### File-Based RuntimeState with No Locking
- **Issue:** `load_runtime_state()` and `save_runtime_state()` read/write `runtime/state.json` without any file locking or atomic operations. Multiple threads (Flask request handler, `CabinetMonitor`, `AutoTransitionController`, `OBSHeartbeat`) call these concurrently.
- **Files:** `src/state.py:38-74`
- **Problem:** Race conditions can corrupt the JSON file or cause `json.JSONDecodeError` on read.
- **Improvement path:** Use `threading.Lock` around load/save, or switch to an in-memory state with periodic snapshot (e.g., SQLite or `shelve`).

### OBSManager Re-Initialization on Every Monitor Loop
- **Issue:** `CabinetMonitor._ensure_obs_manager()` checks connection inside a lock, but if disconnected it creates a new `OBSManager`, re-connects, re-inits the state machine, and re-registers all 4 machines on every loop iteration until connection succeeds.
- **Files:** `src/obs/monitor.py:61-103`
- **Problem:** High CPU and log spam when OBS is offline; state machine YAML is re-parsed each time.
- **Improvement path:** Add an exponential backoff or a "last attempt" timestamp to avoid rapid reconnection loops.

## Fragile Areas

### `sys.path` Manipulation for External `obs_manager`
- **Issue:** Both `src/app.py` and `src/obs/monitor.py` mutate `sys.path` to import `obs_manager` from a sibling directory. `tests/conftest.py` does the same for tests.
- **Files:** `src/app.py:14-17`, `src/obs/monitor.py:11-17`, `tests/conftest.py:6-9`
- **Why fragile:** Breaks if the project is moved, packaged, or run from a different working directory. Also makes the code non-installable.
- **Safe modification:** Convert `obs_manager` to a proper package with a `setup.py` or add it to `PYTHONPATH` via launch script instead of runtime mutation.

### `connected` Property with Internal Exception Swallowing
- **Issue:** `OBSClient.connected` getter catches `Exception` and returns `False`. This hides underlying connection errors, making debugging difficult.
- **Files:** `src/obs/client.py:38-44`
- **Why fragile:** Silent failures mean the UI shows "Disconnected" without any actionable log message.
- **Safe modification:** Log the exception at `DEBUG` or `WARNING` level before returning `False`.

### `confirm_score` Route Has No Transaction Safety
- **Issue:** The route switches OBS scene, then loads configs, computes scores, pushes to scoreboard, and clears pending scores. If any step fails after the scene switch, the scene is already changed but scores may not be pushed.
- **Files:** `src/app.py:156-298`
- **Why fragile:** Partial failure leaves the system in an inconsistent state (wrong scene, pending scores still present or cleared).
- **Safe modification:** Validate everything (configs, schedules, scores) before switching the scene. Treat scene switch as the final commit step.

## Scaling Limits

### Thread Count Grows with Background Workers
- **Current capacity:** 3 daemon threads (`OBSHeartbeat`, `CabinetMonitor`, `AutoTransitionController`) plus Flask's request threads.
- **Limit:** If more background workers are added, the CPython GIL will serialize CPU-bound work (e.g., `process_frame` in `OBSManager` does image recognition).
- **Scaling path:** Move `CabinetMonitor` to a separate process or use `multiprocessing` for the inference pipeline; keep Flask app I/O-bound.

### In-Memory `_machine_states` in AutoTransitionController
- **Current capacity:** Stores state for exactly 4 machines in a plain dict.
- **Limit:** No validation that all 4 machines have reported state before making transition decisions. If a cabinet never emits an update, `all_play` and `all_live_or_blank` may evaluate incorrectly.
- **Scaling path:** Track last-update timestamps and require freshness before considering a machine's state in aggregate decisions.

## Dependencies at Risk

### `obsws-python` Tight Coupling
- **Risk:** `src/obs/client.py` directly imports `obsws_python.ReqClient` and accesses `base_client.ws.connected`. If `obsws-python` changes its internal structure, the `connected` property breaks.
- **Impact:** OBS connection status becomes unreliable.
- **Migration plan:** Wrap all `obsws-python` usage behind the `OBSClient` class and avoid accessing internal attributes; add integration tests against a mock OBS WebSocket server.

### No Dependency Pinning File
- **Risk:** There is no `requirements.txt`, `pyproject.toml`, or `Pipfile` in the repository. Dependencies are installed ad-hoc.
- **Impact:** Different environments may get incompatible package versions (e.g., Flask-SocketIO vs python-socketio version mismatch).
- **Migration plan:** Add a `requirements.txt` or `pyproject.toml` with pinned versions matching the versions specified in `CLAUDE.md`.

## Missing Critical Features

### No Retry Logic for Scoreboard Push
- **Problem:** `ScoreboardPusher._send()` tries once and returns `True`/`False`. A transient network failure means the score is lost unless the operator notices and re-pushes manually.
- **Blocks:** Reliable live broadcast scoring.
- **Fix approach:** Add a retry queue with exponential backoff; emit a failure event to the UI.

### No Health Check Endpoint
- **Problem:** There is no `/health` or `/ready` endpoint for external monitoring (e.g., systemd, Docker, uptime checker).
- **Blocks:** Production deployment automation.
- **Fix approach:** Add a lightweight `/health` route that checks OBS connection and config validity.

## Test Coverage Gaps

### Untested Critical Paths
- **What's not tested:**
  - `confirm_score()` route — the most complex business logic (team 1v1, team 2v2, individual scoring, OBS scene switch, scoreboard push, pending clear).
  - `AutoTransitionController` — no tests for `_tick()`, `proceed()`, `emergency_live()`, or scene resolution.
  - `CabinetMonitor` — no tests for `_run()`, `_ensure_obs_manager()`, or pending-score persistence.
  - `ScoreboardPusher` — no tests for `_send()`, `push_team_score()`, or `push_individual_score()`.
  - `upload_config()` — no tests for file upload, validation, backup, or error paths.
  - `monitor_control()` — no tests for start/stop actions.
  - `automation_delays()`, `automation_pause_resume()`, `automation_proceed()`, `automation_emergency_live()` — no tests.
- **Files:** `src/app.py`, `src/obs/auto_transition.py`, `src/obs/monitor.py`, `src/scoreboard/pusher.py`
- **Risk:** Refactoring any of these modules is dangerous without regression safety.
- **Priority:** High for `confirm_score` and `AutoTransitionController`; Medium for `CabinetMonitor` and `ScoreboardPusher`.

### All API Error Responses Return HTTP 200
- **Issue:** Every `jsonify({"success": False, ...}), 200` returns HTTP 200 even for client errors (invalid input, missing configs, OBS not ready).
- **Files:** `src/app.py` (28 occurrences of `success: False` with status 200)
- **Risk:** HTTP-level monitoring (load balancers, proxies) cannot detect application errors; clients must parse JSON to know if the request failed.
- **Priority:** Medium — not a crash risk, but an API design issue.

## Additional Concerns

### `print()` Used for Monitor Output
- **Issue:** `CabinetMonitor._run()` uses `print(json.dumps(payload))` instead of the module logger.
- **Files:** `src/obs/monitor.py:157`
- **Impact:** Pollutes stdout; cannot be filtered by log level; may interfere with systemd journal parsing.
- **Fix approach:** Replace with `logger.info(...)` or a dedicated structured-log handler.

### No Input Sanitization on File Upload Filename
- **Issue:** `upload_config()` checks `file.filename` against an allow-list, but does not sanitize the filename before writing. While the write path is constructed from the allow-list (`target_filename`), the check itself is case-sensitive and could be bypassed on case-insensitive filesystems.
- **Files:** `src/app.py:384-406`
- **Impact:** Low — the write path is not user-controlled, but the validation logic is brittle.

### `RuntimeState` Default Mutable Dictionaries
- **Issue:** `RuntimeState` uses `field(default_factory=lambda: {...})` correctly for dict fields, but the `load_runtime_state()` function manually reconstructs these defaults inline, creating duplication.
- **Files:** `src/state.py:20-28` (defaults), `src/state.py:58-66` (load function)
- **Impact:** Adding a new field requires edits in two places; risk of drift.
- **Fix approach:** Use `RuntimeState(**data)` with `dataclasses.fields()` default handling, or rely on Pydantic models for validation + defaults.

---

*Concerns audit: 2026-04-22*

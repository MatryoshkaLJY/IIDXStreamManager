# Testing Patterns

**Analysis Date:** 2026-04-22

## Test Framework

**Runner:**
- pytest (version not pinned, no config file detected)
- No `pytest.ini`, `setup.cfg`, `pyproject.toml`, or `tox.ini` found
- No coverage configuration detected

**Assertion Library:**
- Standard pytest assertions (`assert` statements)
- `pytest.raises()` for exception testing

**Run Commands:**
```bash
pytest                    # Run all tests (inferred)
pytest -v                 # Verbose output (inferred)
```

## Test File Organization

**Location:**
- All tests in `/tests/` directory at project root
- Tests are NOT co-located with source files

**Naming:**
- `test_<module_name>.py` pattern
- Test classes use `Test<Subject>`: `TestRuntimeState`, `TestSaveRuntimeState`, `TestLoadRuntimeState`, `TestOBSClient`, `TestOBSHeartbeat`, `TestSceneController`, `TestAppObsRoutes`, `TestSocketIOObsReconnect`
- Test methods use descriptive `snake_case`: `test_client_stores_params_without_connecting`, `test_heartbeat_starts_and_stops_without_crash`

**Structure:**
```
tests/
├── conftest.py                # Shared fixtures and sys.path setup
├── test_app_obs_routes.py     # Flask route + SocketIO tests
├── test_config_loader.py      # Config loading and validation tests
├── test_config_models.py      # Pydantic model validation tests
├── test_heartbeat.py          # OBSHeartbeat daemon thread tests
├── test_obs_client.py         # OBSClient wrapper tests
├── test_scene_controller.py   # SceneController logic tests
└── test_state.py              # RuntimeState persistence tests
```

## Test Structure

**Suite Organization:**
```python
class TestSceneController:
    def test_validate_scenes_returns_false_when_not_connected(self):
        ...

    def test_switch_to_calls_set_current_program_scene_for_valid_scene(self):
        ...
```

**Patterns:**
- Class-based grouping by subject under test
- No `setUp`/`tearDown` methods; each test is self-contained
- `tmp_path` pytest fixture used for filesystem tests
- `tempfile.TemporaryDirectory()` used directly in some tests

## Mocking

**Framework:**
- `unittest.mock` (standard library): `MagicMock`, `Mock`, `patch`, `patch.object`
- No `pytest-mock` or `mockito` detected

**Patterns:**

Patching external SDK imports:
```python
with patch("src.obs.client.obsws_python.ReqClient") as mock_req:
    client = OBSClient(host="obs.local", port=4444, password="secret")
    client.connect()
    mock_req.assert_called_once_with(
        host="obs.local", port=4444, password="secret", timeout=3
    )
```

Mocking with `spec` for type safety:
```python
obs = MagicMock(spec=OBSClient)
obs.connected = False
```

Patching object methods:
```python
with patch.object(app._scene_controller, "switch_to", return_value=(True, "")):
    ...
```

**What to Mock:**
- External OBS WebSocket SDK (`obsws_python.ReqClient`)
- Flask-SocketIO (`SocketIO.test_client`)
- Internal collaborators (`OBSClient`, `SceneController`)
- Runtime state persistence (`save_runtime_state`)

**What NOT to Mock:**
- Pydantic model validation (tested directly with real data)
- JSON serialization/deserialization
- Dataclass instantiation

## Fixtures and Factories

**Test Data:**
- Inline dictionaries in test methods (no shared fixtures)
- Example from `test_config_models.py`:
```python
def test_valid_teams_config():
    data = {
        "teams": [
            {
                "id": "team1",
                "name": "Team One",
                "emoji": "🦁",
                ...
            }
        ]
    }
    config = TeamsConfig.model_validate(data)
    assert len(config.teams) == 1
```

**conftest.py:**
```python
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
parent_dir = str(project_root.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
```
- Only contains `sys.path` manipulation for sibling-directory `obs_manager` imports
- No pytest fixtures defined

## Coverage

**Requirements:**
- No coverage target enforced
- No coverage config detected

**View Coverage:**
```bash
pytest --cov=src --cov-report=term-missing    # Inferred standard command
```

## Test Types

**Unit Tests:**
- Pure logic tests for `RuntimeState`, Pydantic models, `SceneController`
- Mocked external dependencies
- Fast, isolated, no I/O

**Integration Tests:**
- `test_app_obs_routes.py` tests Flask app factory and HTTP routes with `app.test_client()`
- `test_state.py` tests JSON file roundtrip persistence
- `test_config_loader.py` tests filesystem I/O with `tmp_path`

**E2E Tests:**
- Not used
- No Selenium, Playwright, or browser automation detected

**SocketIO Tests:**
- `TestSocketIOObsReconnect` uses Flask-SocketIO's test client:
```python
app, socketio = create_app(return_socketio=True)
test_client = socketio.test_client(app)
test_client.emit("obs_reconnect")
received = test_client.get_received()
```

## Common Patterns

**Async Testing:**
- Not directly tested; async code (`ScoreboardPusher._send_async`) has no tests
- `asyncio.run()` usage in production is not covered

**Error Testing:**
```python
def test_get_version_raises_when_not_connected(self):
    client = OBSClient()
    with pytest.raises(RuntimeError, match="not connected"):
        client.get_version()
```

**Threading/Daemon Tests:**
```python
def test_heartbeat_starts_and_stops_without_crash(self):
    obs = Mock()
    socketio = Mock()
    hb = OBSHeartbeat(obs, socketio, interval=0.1)
    hb.start()
    assert hb._thread is not None
    assert hb._thread.is_alive()
    hb.stop()
    assert not hb._thread.is_alive()
```
- Uses `time.sleep(0.25)` for timing-dependent assertions
- Tests verify side effects on mock objects (`socketio.emit.call_count`)

**State Roundtrip Tests:**
```python
def test_returns_matching_values_after_save(self):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "state.json"
        original = RuntimeState(...)
        save_runtime_state(original, path)
        loaded = load_runtime_state(path)
        assert loaded.config_paths == original.config_paths
```

## Coverage Gaps

**Untested Modules:**
- `src/scoreboard/pusher.py` — No tests for `ScoreboardPusher` (WebSocket scoreboard pushing)
- `src/obs/monitor.py` — No tests for `CabinetMonitor` (daemon thread, OBSManager integration)
- `src/obs/auto_transition.py` — No tests for `AutoTransitionController` (complex automation logic)

**Untested Functionality:**
- WebSocket scoreboard communication (`websockets` async calls)
- OBS scene auto-transition logic (aggregate state machine, delay timers, emergency live)
- Cabinet monitoring loop (frame processing, state machine integration with external `obs_manager`)
- File upload and backup logic in `/upload_config` route
- Score confirmation and scoreboard push logic in `/confirm_score` route
- Automation pause/resume/proceed/emergency endpoints
- Monitoring start/stop control endpoint

**Risk Assessment:**
- The most complex and business-critical code (`AutoTransitionController`, `CabinetMonitor`, `ScoreboardPusher`) has zero test coverage
- These modules involve threading, external WebSocket connections, and stateful logic — exactly where bugs are most likely and most impactful

---

*Testing analysis: 2026-04-22*

import json
import tempfile
from pathlib import Path

import pytest

from src.state import RuntimeState, load_runtime_state, save_runtime_state


class TestRuntimeState:
    def test_can_be_instantiated_with_config_paths_and_configs(self):
        state = RuntimeState(
            config_paths={"teams": "/path/to/teams.json"},
            loaded_at="2026-04-15T10:00:00",
        )
        assert state.config_paths == {"teams": "/path/to/teams.json"}
        assert state.loaded_at == "2026-04-15T10:00:00"

    def test_default_state_has_empty_config_paths_and_none_loaded_at(self):
        state = RuntimeState()
        assert state.config_paths == {}
        assert state.loaded_at is None


class TestSaveRuntimeState:
    def test_writes_json_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            state = RuntimeState(
                config_paths={"teams": "data/teams.json"},
                loaded_at="2026-04-15T10:00:00",
            )
            save_runtime_state(state, path)
            assert path.exists()
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data["config_paths"] == {"teams": "data/teams.json"}
            assert data["loaded_at"] == "2026-04-15T10:00:00"

    def test_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "runtime" / "state.json"
            state = RuntimeState(config_paths={}, loaded_at=None)
            save_runtime_state(state, path)
            assert path.exists()


class TestLoadRuntimeState:
    def test_returns_matching_values_after_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            original = RuntimeState(
                config_paths={"teams": "data/teams.json"},
                loaded_at="2026-04-15T10:00:00",
            )
            save_runtime_state(original, path)
            loaded = load_runtime_state(path)
            assert loaded.config_paths == {"teams": "data/teams.json"}
            assert loaded.loaded_at == "2026-04-15T10:00:00"

    def test_returns_default_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.json"
            loaded = load_runtime_state(path)
            assert loaded.config_paths == {}
            assert loaded.loaded_at is None


class TestCreateApp:
    def test_create_app_returns_flask_app(self):
        from src.app import create_app

        app = create_app()
        assert app is not None
        assert hasattr(app, "name")

    def test_app_has_socketio_attached(self):
        from src.app import create_app

        app, socketio = create_app(return_socketio=True)
        assert socketio is not None
        assert hasattr(socketio, "run")

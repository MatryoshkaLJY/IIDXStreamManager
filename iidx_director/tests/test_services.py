import sys

import pytest

from src.services import DependencyManager, ServiceSpec, ServiceStartupError, default_service_specs


def test_default_specs_use_repository_paths(tmp_path):
    specs = default_service_specs(tmp_path)
    assert [spec.name for spec in specs] == [
        "state-reco",
        "score-reco",
        "bpl-scoreboard",
        "knockout-scoreboard",
        "sceneinfo",
    ]
    assert [spec.port for spec in specs] == [9876, 9877, 8080, 8081, 8082]


def test_manager_starts_and_stops_owned_process(tmp_path):
    spec = ServiceSpec(
        "http",
        (sys.executable, "-m", "http.server", "18991", "--bind", "127.0.0.1"),
        tmp_path,
        18991,
    )
    manager = DependencyManager(tmp_path, specs=(spec,), startup_timeout=3)

    manager.start()
    assert "http" in manager.owned_processes
    manager.stop()
    assert manager.owned_processes == {}


def test_manager_rejects_missing_workdir(tmp_path):
    spec = ServiceSpec(
        "missing",
        (sys.executable, "-c", "pass"),
        tmp_path / "missing",
        18992,
    )
    manager = DependencyManager(tmp_path, specs=(spec,), startup_timeout=1)

    with pytest.raises(ServiceStartupError, match="工作目录不存在"):
        manager.start()

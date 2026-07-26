import pytest

from src.scene import PendingError, SceneCoordinator


def test_scene_aliases_normalize_to_actual_obs_names():
    coordinator = SceneCoordinator({"team_sp_1v1": "SP团队赛"})
    assert coordinator.resolve("team_sp_1v1") == "SP_BPL"
    assert coordinator.resolve("DP_Arena") == "DP_Arena"
    assert coordinator.resolve("Scoreboard_web") == "Scoreboard_web"


def test_pending_is_single_and_scene_snapshots_are_independent():
    coordinator = SceneCoordinator()
    pending = coordinator.create_pending(
        "SP_BPL", "sp_bpl", {"left_team_name": "A"}, {"left": 10}, source="shortcut"
    )
    with pytest.raises(PendingError):
        coordinator.create_pending("SP_Arena", "sp_arena", source="shortcut")
    coordinator.mark("staged")
    coordinator.mark("scene_switched")
    coordinator.complete()

    assert coordinator.pending is None
    assert coordinator.snapshot("SP_BPL")["texts"] == {"left_team_name": "A"}
    assert coordinator.snapshot("SP_Arena")["texts"] == {}
    assert pending.scene == "SP_BPL"


def test_failed_pending_can_be_cancelled_or_retried():
    coordinator = SceneCoordinator()
    coordinator.create_pending("Live", "live", source="shortcut")
    coordinator.mark("failed", failed_stage="scene_switch", error="OBS down")
    assert coordinator.pending.to_dict()["error"] == "OBS down"
    coordinator.mark("scene_switched")
    coordinator.complete()
    assert coordinator.active_scene == "Live"

#!/usr/bin/env python3
"""Unit tests for IIDXStateMachineManager multi-machine support."""

import sys
import os

# Allow running from either iidx_state_machine/ or the project root
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state_machine import IIDXStateMachineManager


def test_two_machines_independent():
    """Two machines fed different events must diverge to independent states."""
    config_path = os.path.join(os.path.dirname(__file__), "state_machine.yaml")
    mgr = IIDXStateMachineManager(config_path, log_level="ERROR")

    mgr.add_machine("m1")
    mgr.add_machine("m2")

    # Both start in IDLE
    assert mgr.list_machines() == ["m1", "m2"]
    assert mgr.get_machine_state("m1")["current_state"] == "IDLE"
    assert mgr.get_machine_state("m2")["current_state"] == "IDLE"

    # m1: IDLE -> ENTRY -> MODESEL
    r1 = mgr.process_event("m1", "entry")
    assert r1["machine_id"] == "m1"
    assert r1["current_state"] == "ENTRY"

    r2 = mgr.process_event("m1", "modesel")
    assert r2["current_state"] == "MODESEL"

    # m2 stays IDLE
    assert mgr.get_machine_state("m2")["current_state"] == "IDLE"

    # m2: IDLE -> ENTRY
    r3 = mgr.process_event("m2", "entry")
    assert r3["current_state"] == "ENTRY"

    # m1 still MODESEL
    assert mgr.get_machine_state("m1")["current_state"] == "MODESEL"
    assert mgr.get_machine_state("m2")["current_state"] == "ENTRY"

    print("[✓] test_two_machines_independent passed")


def test_machine_lifecycle():
    """Adding and removing machines works correctly."""
    config_path = os.path.join(os.path.dirname(__file__), "state_machine.yaml")
    mgr = IIDXStateMachineManager(config_path, log_level="ERROR")

    mgr.add_machine("cab1")
    assert "cab1" in mgr.list_machines()

    mgr.remove_machine("cab1")
    assert "cab1" not in mgr.list_machines()

    try:
        mgr.process_event("cab1", "entry")
        assert False, "Should raise ValueError for removed machine"
    except ValueError:
        pass

    print("[✓] test_machine_lifecycle passed")


def test_duplicate_machine_id():
    """Duplicate machine IDs should raise ValueError."""
    config_path = os.path.join(os.path.dirname(__file__), "state_machine.yaml")
    mgr = IIDXStateMachineManager(config_path, log_level="ERROR")

    mgr.add_machine("cab1")
    try:
        mgr.add_machine("cab1")
        assert False, "Should raise ValueError for duplicate machine_id"
    except ValueError:
        pass

    print("[✓] test_duplicate_machine_id passed")


def test_score_transition_triggers_action():
    """Entering a SCORE state should trigger the get_score action."""
    config_path = os.path.join(os.path.dirname(__file__), "state_machine.yaml")
    mgr = IIDXStateMachineManager(config_path, log_level="ERROR")

    mgr.add_machine("m1")

    # Navigate: IDLE -> ENTRY -> MODESEL -> S_SONGSEL -> S_PLAY -> S_SCORE
    mgr.process_event("m1", "entry")
    mgr.process_event("m1", "modesel")
    mgr.process_event("m1", "songsel")
    mgr.process_event("m1", "play1")
    result = mgr.process_event("m1", "score")

    assert result["current_state"] == "S_SCORE"
    assert "get_score" in result.get("actions_triggered", [])
    assert result["handled"] is True

    print("[✓] test_score_transition_triggers_action passed")


def main():
    print("=" * 50)
    print("IIDXStateMachineManager tests")
    print("=" * 50)
    test_two_machines_independent()
    test_machine_lifecycle()
    test_duplicate_machine_id()
    test_score_transition_triggers_action()
    print("=" * 50)
    print("All tests passed")
    print("=" * 50)


if __name__ == "__main__":
    main()

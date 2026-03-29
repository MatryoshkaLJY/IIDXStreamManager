"""
用真实识别数据测试状态机

用法:
    python3 test_with_real_data.py /tmp/kbpl_states.txt
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from state_machine import IIDXStateMachine


def test_with_sequence(states_file: str):
    """从文件读取状态序列并测试状态机"""
    with open(states_file) as f:
        states = [line.strip() for line in f if line.strip()]

    print(f"Loaded {len(states)} frames from {states_file}")
    print("=" * 70)

    sm = IIDXStateMachine(debounce_frames=2)

    transitions = []
    for i, state in enumerate(states):
        prev = sm.state
        current = sm.feed(state)
        if prev != current:
            transitions.append((i, prev.value, current.value))
            print(f"[{i+1:3}] {state:12} -> TRANSITION: {prev.value:12} -> {current.value}")
        else:
            print(f"[{i+1:3}] {state:12}    (stable)")

    print("=" * 70)
    print(f"Total transitions: {len(transitions)}")
    print(f"Final status: {sm.get_status()}")

    print("\nTransition summary:")
    for frame, from_s, to_s in transitions:
        print(f"  Frame {frame+1}: {from_s} -> {to_s}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <states_file>")
        sys.exit(1)

    test_with_sequence(sys.argv[1])

"""状态机使用示例和简单演示"""

import time

from state_machine import IIDXStateMachine, State


def demo_basic():
    """基础演示：模拟一轮标准模式游戏"""
    print("=" * 60)
    print("Demo: 标准模式一局游戏")
    print("=" * 60)

    sm = IIDXStateMachine()

    # 模拟帧序列：idle -> interlude -> entry -> ... -> play -> score -> interlude
    frames = [
        State.IDLE,
        State.IDLE,           # 防抖确认
        State.INTERLUDE,
        State.INTERLUDE,
        State.ENTRY,
        State.ENTRY,
        State.INTERLUDE,
        State.INTERLUDE,
        State.MODESEL,
        State.MODESEL,
        State.PAY,
        State.PAY,
        State.INTERLUDE,
        State.INTERLUDE,
        State.SONGSEL,        # 选曲
        State.SONGSEL,
        State.CONFIRM,        # 确认
        State.CONFIRM,
        State.PLAY,           # 开始游玩
        State.PLAY,
        State.PLAY,
        State.PLAY,
        State.SCORE,          # 成绩
        State.SCORE,
        State.INTERLUDE,      # 回到过渡
        State.INTERLUDE,
        State.ENTRY,          # 新一轮或结束
        State.ENTRY,
    ]

    for i, frame in enumerate(frames):
        print(f"\n[Frame {i+1:2}] Input: {frame.value}")
        sm.feed(frame)
        time.sleep(0.05)  # 模拟帧间隔

    print("\n" + "=" * 60)
    print("Final Status:", sm.get_status())
    print("=" * 60)


def demo_dan_mode():
    """演示：段位模式（多首曲目，死亡后结束）"""
    print("\n" + "=" * 60)
    print("Demo: 段位模式（3首后死亡）")
    print("=" * 60)

    sm = IIDXStateMachine()

    # 模拟 Dan 模式流程
    frames = [
        # 进入 Dan 模式
        State.IDLE, State.IDLE,
        State.INTERLUDE, State.INTERLUDE,
        State.ENTRY, State.ENTRY,
        State.INTERLUDE, State.INTERLUDE,
        State.DANSEL, State.DANSEL,      # 选段位
        State.CONFIRM, State.CONFIRM,

        # 第一首
        State.PLAY, State.PLAY,
        State.SCORE, State.SCORE,
        State.INTERLUDE, State.INTERLUDE,

        # 第二首
        State.PLAY, State.PLAY,
        State.SCORE, State.SCORE,
        State.INTERLUDE, State.INTERLUDE,

        # 第三首（失败）
        State.PLAY, State.PLAY,
        State.DEATH, State.DEATH,        # 血条归零
        State.DANSCORE, State.DANSCORE,  # 段位结算
        State.INTERLUDE, State.INTERLUDE,
        State.ENTRY, State.ENTRY,
    ]

    for i, frame in enumerate(frames):
        print(f"\n[Frame {i+1:2}] Input: {frame.value}")
        sm.feed(frame)
        time.sleep(0.05)

    print("\n" + "=" * 60)
    print("Final Status:", sm.get_status())
    print("=" * 60)


def demo_arena_mode():
    """演示：Arena 模式（多轮对战）"""
    print("\n" + "=" * 60)
    print("Demo: Arena 模式（2轮对战）")
    print("=" * 60)

    sm = IIDXStateMachine()

    frames = [
        State.IDLE, State.IDLE,
        State.INTERLUDE, State.INTERLUDE,
        State.ENTRY, State.ENTRY,
        State.INTERLUDE, State.INTERLUDE,
        State.MODESEL, State.MODESEL,

        # Arena 等待
        State.AWAIT, State.AWAIT,
        State.INTERLUDE, State.INTERLUDE,

        # 第一轮
        State.SONGSEL, State.SONGSEL,
        State.INTERLUDE, State.INTERLUDE,
        State.ACONFIRM, State.ACONFIRM,
        State.CONFIRM, State.CONFIRM,
        State.PLAY, State.PLAY,
        State.SCORE, State.SCORE,
        State.INTERLUDE, State.INTERLUDE,

        # 第二轮
        State.SONGSEL, State.SONGSEL,
        State.INTERLUDE, State.INTERLUDE,
        State.ACONFIRM, State.ACONFIRM,
        State.CONFIRM, State.CONFIRM,
        State.PLAY, State.PLAY,
        State.SCORE, State.SCORE,
        State.INTERLUDE, State.INTERLUDE,

        # 结算
        State.ARANK, State.ARANK,
        State.INTERLUDE, State.INTERLUDE,
        State.ENTRY, State.ENTRY,
    ]

    for i, frame in enumerate(frames):
        print(f"\n[Frame {i+1:2}] Input: {frame.value}")
        sm.feed(frame)
        time.sleep(0.05)

    print("\n" + "=" * 60)
    print("Final Status:", sm.get_status())
    print("=" * 60)


def demo_with_custom_callback():
    """演示：自定义状态转移回调"""
    print("\n" + "=" * 60)
    print("Demo: 自定义回调")
    print("=" * 60)

    def my_callback(from_state, to_state, context):
        print(f"  >> 自定义处理: {from_state.value} -> {to_state.value}")
        if to_state == State.PLAY:
            print("  >> 🎵 音乐开始！")
        elif to_state == State.DEATH:
            print("  >> 💀 曲失败！")
        elif to_state == State.SCORE:
            print("  >> 📝 记录成绩")

    sm = IIDXStateMachine(on_transition=my_callback)

    frames = [
        State.IDLE, State.IDLE,
        State.PLAY, State.PLAY,
        State.DEATH, State.DEATH,
        State.SCORE, State.SCORE,
    ]

    for frame in frames:
        sm.feed(frame)
        time.sleep(0.1)


if __name__ == "__main__":
    demo_basic()
    demo_dan_mode()
    demo_arena_mode()
    demo_with_custom_callback()

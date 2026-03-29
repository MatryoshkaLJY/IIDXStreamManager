"""测试套件"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import unittest

from state_machine import IIDXStateMachine, State, GameMode


class TestStateMachine(unittest.TestCase):
    """状态机单元测试"""

    def test_initial_state(self):
        """测试初始状态"""
        sm = IIDXStateMachine()
        self.assertEqual(sm.state, State.IDLE)

    def test_debounce(self):
        """测试防抖机制"""
        sm = IIDXStateMachine(debounce_frames=2)

        # 只输入一帧，不应该转移
        sm.feed(State.INTERLUDE)
        self.assertEqual(sm.state, State.IDLE)

        # 输入相同第二帧，应该转移
        sm.feed(State.INTERLUDE)
        self.assertEqual(sm.state, State.INTERLUDE)

    def test_debounce_3_frames(self):
        """测试 3 帧防抖"""
        sm = IIDXStateMachine(debounce_frames=3)

        sm.feed(State.INTERLUDE)
        sm.feed(State.INTERLUDE)
        self.assertEqual(sm.state, State.IDLE)  # 还不够

        sm.feed(State.INTERLUDE)
        self.assertEqual(sm.state, State.INTERLUDE)  # 达到 3 帧，转移

    def test_mode_detection_standard(self):
        """测试标准模式检测：interlude -> songsel"""
        sm = IIDXStateMachine()

        # 先进入 interlude
        sm.feed(State.INTERLUDE)
        sm.feed(State.INTERLUDE)
        self.assertEqual(sm.context.mode, GameMode.UNKNOWN)

        # 从 interlude 进入 songsel 才确定模式
        sm.feed(State.SONGSEL)
        sm.feed(State.SONGSEL)
        self.assertEqual(sm.context.mode, GameMode.STANDARD)

    def test_mode_detection_dan(self):
        """测试段位模式检测：interlude -> dansel"""
        sm = IIDXStateMachine()

        # 先进入 interlude
        sm.feed(State.INTERLUDE)
        sm.feed(State.INTERLUDE)
        self.assertEqual(sm.context.mode, GameMode.UNKNOWN)

        # 从 interlude 进入 dansel 才确定模式
        sm.feed(State.DANSEL)
        sm.feed(State.DANSEL)
        self.assertEqual(sm.context.mode, GameMode.DAN)

    def test_mode_detection_arena(self):
        """测试 Arena 模式检测：interlude -> await"""
        sm = IIDXStateMachine()

        # 先进入 interlude
        sm.feed(State.INTERLUDE)
        sm.feed(State.INTERLUDE)
        self.assertEqual(sm.context.mode, GameMode.UNKNOWN)

        # 从 interlude 进入 await 才确定模式
        sm.feed(State.AWAIT)
        sm.feed(State.AWAIT)
        self.assertEqual(sm.context.mode, GameMode.ARENA)

    def test_song_counting(self):
        """测试曲目计数"""
        sm = IIDXStateMachine()

        # 建立合法路径: idle -> interlude -> confirm -> play
        sm.feed(State.INTERLUDE)
        sm.feed(State.INTERLUDE)
        sm.feed(State.CONFIRM)
        sm.feed(State.CONFIRM)

        # 第一首
        sm.feed(State.PLAY)
        sm.feed(State.PLAY)
        self.assertEqual(sm.context.song_count, 1)

        # 第二首: play -> interlude -> play
        sm.feed(State.INTERLUDE)
        sm.feed(State.INTERLUDE)
        sm.feed(State.PLAY)
        sm.feed(State.PLAY)
        self.assertEqual(sm.context.song_count, 2)

    def test_context_reset_on_entry(self):
        """测试 entry 触发重置 - 新玩家上机"""
        sm = IIDXStateMachine()

        # 先进行一些游戏
        sm.feed(State.INTERLUDE)
        sm.feed(State.INTERLUDE)
        sm.feed(State.CONFIRM)
        sm.feed(State.CONFIRM)
        sm.feed(State.PLAY)
        sm.feed(State.PLAY)
        sm.feed(State.SCORE)
        sm.feed(State.SCORE)

        # 玩家下机: score -> interlude -> entry
        sm.feed(State.INTERLUDE)
        sm.feed(State.INTERLUDE)
        sm.feed(State.ENTRY)
        sm.feed(State.ENTRY)

        # 此时 game_active 应该为 False，但计数还未重置
        self.assertFalse(sm.context.game_active)
        self.assertEqual(sm.context.song_count, 1)  # 未重置

        # 机器空闲判定: entry -> blank
        sm.feed(State.BLANK)
        sm.feed(State.BLANK)

        # 此时才真正重置
        status = sm.get_status()
        self.assertTrue(status["machine_idle"])

    def test_machine_idle_detection(self):
        """测试机器空闲判定: entry -> blank"""
        sm = IIDXStateMachine()

        # 模拟游戏流程
        sm.feed(State.INTERLUDE)
        sm.feed(State.INTERLUDE)
        sm.feed(State.PLAY)
        sm.feed(State.PLAY)
        self.assertTrue(sm.context.game_active)

        # 游戏结束 -> entry -> blank
        sm.feed(State.SCORE)
        sm.feed(State.SCORE)
        sm.feed(State.INTERLUDE)
        sm.feed(State.INTERLUDE)
        sm.feed(State.ENTRY)
        sm.feed(State.ENTRY)
        self.assertFalse(sm.context.game_active)

        # entry -> blank = 机器空闲
        sm.feed(State.BLANK)
        sm.feed(State.BLANK)
        status = sm.get_status()
        self.assertTrue(status["machine_idle"])
        self.assertEqual(sm.context.song_count, 0)  # 已重置

    def test_dan_death_break(self):
        """测试 Dan 模式死亡跳出"""
        sm = IIDXStateMachine()

        # 建立 Dan 模式路径: interlude -> dansel
        sm.feed(State.INTERLUDE)
        sm.feed(State.INTERLUDE)
        sm.feed(State.DANSEL)
        sm.feed(State.DANSEL)
        self.assertEqual(sm.context.mode, GameMode.DAN)

        # 进入 confirm -> play
        sm.feed(State.CONFIRM)
        sm.feed(State.CONFIRM)
        sm.feed(State.PLAY)
        sm.feed(State.PLAY)
        self.assertTrue(sm.context.in_song_cycle)

        # 死亡
        sm.feed(State.DEATH)
        sm.feed(State.DEATH)

        # Dan 模式下死亡应该跳出曲目进程
        self.assertFalse(sm.context.in_song_cycle)

    def test_invalid_transition_blocked(self):
        """测试非法转移被阻止"""
        sm = IIDXStateMachine()

        # IDLE 不能直接到 PLAY（必须经过 interlude 等）
        sm.feed(State.PLAY)
        sm.feed(State.PLAY)
        self.assertEqual(sm.state, State.IDLE)  # 被阻止，保持 IDLE

    def test_transition_history(self):
        """测试转移历史记录"""
        sm = IIDXStateMachine()

        sm.feed(State.INTERLUDE)
        sm.feed(State.INTERLUDE)
        sm.feed(State.ENTRY)
        sm.feed(State.ENTRY)

        history = sm.transition_history
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0], (State.IDLE, State.INTERLUDE))
        self.assertEqual(history[1], (State.INTERLUDE, State.ENTRY))

    def test_from_string(self):
        """测试字符串转状态"""
        self.assertEqual(State.from_string("play"), State.PLAY)
        self.assertEqual(State.from_string("PLAY"), State.PLAY)
        self.assertEqual(State.from_string("unknown"), State.OTHERS)

    def test_callback_invoked(self):
        """测试回调函数被调用"""
        called = []

        def callback(from_s, to_s, ctx):
            called.append((from_s, to_s))

        sm = IIDXStateMachine(on_transition=callback)
        sm.feed(State.INTERLUDE)
        sm.feed(State.INTERLUDE)

        self.assertEqual(len(called), 1)
        self.assertEqual(called[0], (State.IDLE, State.INTERLUDE))


class TestStateContext(unittest.TestCase):
    """测试状态上下文"""

    def test_reset(self):
        """测试上下文重置"""
        from state_machine import StateContext

        ctx = StateContext()
        ctx.mode = GameMode.DAN
        ctx.song_count = 3
        ctx.in_song_cycle = True
        ctx.death_occurred = True

        ctx.reset()

        self.assertEqual(ctx.mode, GameMode.UNKNOWN)
        self.assertEqual(ctx.song_count, 0)
        self.assertFalse(ctx.in_song_cycle)
        self.assertFalse(ctx.death_occurred)


if __name__ == "__main__":
    unittest.main()

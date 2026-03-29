"""
IIDX Stream State Machine

根据 CLAUDE.md 设计实现的游戏状态机，用于配合 OBS 场景切换。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class State(Enum):
    """IIDX 游戏状态枚举"""

    # 基础状态
    IDLE = "idle"                    # 机器闲置
    INTERLUDE = "interlude"          # 过渡/加载
    ENTRY = "entry"                  # 玩家登入/登出
    MODESEL = "modesel"              # 模式选择
    PAY = "pay"                      # 投币/支付
    SONGSEL = "songsel"              # 选曲
    CONFIRM = "confirm"              # 曲目确认
    # 游玩状态（细分为四种类型）
    PLAY1 = "play1"                  # 1P 游玩
    PLAY2 = "play2"                  # 2P 游玩
    PLAY12 = "play12"                # 1P+2P 同时游玩
    PLAYD = "playd"                  # DP 游玩
    PLAY = "play"                    # 通用游玩（向后兼容）
    DEATH = "death"                  # 曲失败
    SCORE = "score"                  # 成绩结算

    # 对战模式特有
    BWAIT = "bwait"                  # BPL 等待
    BSEL = "bsel"                    # BPL 选曲
    BRANK = "brank"                  # BPL 排名

    # Arena 模式特有
    AWAIT = "await"                  # Arena 等待
    ACONFIRM = "aconfirm"            # Arena 确认
    ASUM = "asum"                    # Arena 总分
    ARANK = "arank"                  # Arena 排名

    # Dan 模式特有
    DANSEL = "dansel"                # 段位选择
    DANSCORE = "danscore"            # 段位结算

    # 其他
    BLANK = "blank"                  # 黑屏
    SPLASH = "splash"                # 开场动画
    LAB = "lab"                      # 实验室/测试
    OTHERS = "others"                # 其他未分类
    SET = "set"                      # 设置画面

    @classmethod
    def from_string(cls, s: str) -> State:
        """从字符串创建状态"""
        try:
            return cls(s.lower())
        except ValueError:
            logger.warning(f"Unknown state: {s}, defaulting to OTHERS")
            return cls.OTHERS

    @classmethod
    def play_states(cls) -> set[State]:
        """获取所有游玩状态集合"""
        return {cls.PLAY1, cls.PLAY2, cls.PLAY12, cls.PLAYD, cls.PLAY}

    def is_play_state(self) -> bool:
        """检查是否是游玩状态"""
        return self in self.play_states()


class GameMode(Enum):
    """游戏模式"""
    UNKNOWN = auto()
    STANDARD = auto()        # 标准模式
    BPL_BATTLE = auto()      # BPL 对战
    ARENA = auto()           # 竞技场
    DAN = auto()             # 段位认定


@dataclass
class StateContext:
    """状态机上下文，记录当前游戏会话的信息"""
    mode: GameMode = GameMode.UNKNOWN
    song_count: int = 0           # 当前已游玩曲目数（同一首歌多次尝试只计1次）
    try_count: int = 0            # 当前曲目的尝试次数
    in_song_cycle: bool = False   # 是否在【曲目进程】中
    death_occurred: bool = False  # 本轮是否发生过 DEATH
    game_active: bool = False     # 是否有玩家正在进行游戏
    _last_song_completed: bool = False  # 上一首歌是否正常完成（用于检测快捷重启）

    def reset(self):
        """重置上下文（新一轮游戏）"""
        self.mode = GameMode.UNKNOWN
        self.song_count = 0
        self.try_count = 0
        self.in_song_cycle = False
        self.death_occurred = False
        self.game_active = False
        self._last_song_completed = False


# 状态转移回调函数类型
StateTransitionCallback = Callable[[State, State, StateContext], None]


class IIDXStateMachine:
    """
    IIDX 游戏状态机

    特点：
    1. 防抖机制：连续两帧相同状态才进行状态转移
    2. 模式感知：自动检测并跟踪游戏模式
    3. 曲目进程追踪：正确处理 play/death/score/interlude 循环
    4. 异常重置：检测到 entry 时可重置状态机
    """

    def __init__(
        self,
        on_transition: Optional[StateTransitionCallback] = None,
        debounce_frames: int = 2
    ):
        """
        初始化状态机

        Args:
            on_transition: 状态转移回调函数 (from_state, to_state, context) -> None
            debounce_frames: 防抖帧数，默认 2 帧
        """
        self._state = State.IDLE
        self._context = StateContext()
        self._on_transition = on_transition or self._default_transition_handler
        self._debounce_frames = debounce_frames

        # 防抖缓冲区
        self._frame_buffer: list[State] = []
        self._last_confirmed_state: State = State.IDLE

        # 转移历史（用于调试）
        self._transition_history: list[tuple[State, State]] = []

    @property
    def state(self) -> State:
        """当前状态"""
        return self._state

    @property
    def context(self) -> StateContext:
        """当前上下文"""
        return self._context

    @property
    def transition_history(self) -> list[tuple[State, State]]:
        """状态转移历史"""
        return self._transition_history.copy()

    def reset(self, new_state: State = State.IDLE):
        """重置状态机"""
        old_state = self._state
        self._state = new_state
        self._context.reset()
        self._frame_buffer.clear()
        self._last_confirmed_state = new_state

        if old_state != new_state:
            self._transition_history.append((old_state, new_state))
            self._on_transition(old_state, new_state, self._context)

        logger.info(f"State machine reset to {new_state.value}")

    def feed(self, recognized_state: State | str) -> State:
        """
        输入一帧的识别结果

        Args:
            recognized_state: 识别出的状态（State 枚举或字符串）

        Returns:
            当前状态（可能已发生转移）
        """
        if isinstance(recognized_state, str):
            recognized_state = State.from_string(recognized_state)

        # 加入防抖缓冲区
        self._frame_buffer.append(recognized_state)

        # 保持缓冲区大小
        if len(self._frame_buffer) > self._debounce_frames:
            self._frame_buffer.pop(0)

        # 检查防抖条件：缓冲区满且所有帧状态相同
        if len(self._frame_buffer) >= self._debounce_frames:
            if all(s == self._frame_buffer[0] for s in self._frame_buffer):
                confirmed_state = self._frame_buffer[0]
                if confirmed_state != self._state:
                    self._try_transition(confirmed_state)

        return self._state

    def _try_transition(self, new_state: State):
        """尝试执行状态转移"""
        old_state = self._state

        # 检查是否是合法转移
        if not self._is_valid_transition(old_state, new_state):
            logger.debug(f"Ignoring invalid transition: {old_state.value} -> {new_state.value}")
            return

        # 更新模式上下文
        self._update_context(old_state, new_state)

        # 执行转移
        self._state = new_state
        self._transition_history.append((old_state, new_state))

        logger.info(f"State transition: {old_state.value} -> {new_state.value}")
        self._on_transition(old_state, new_state, self._context)

    def _is_valid_transition(self, from_state: State, to_state: State) -> bool:
        """检查状态转移是否合法"""
        # 相同状态无需转移
        if from_state == to_state:
            return False

        # 通用有效转移
        valid_transitions = self._get_valid_transitions(from_state)
        return to_state in valid_transitions

    def _get_valid_transitions(self, state: State) -> set[State]:
        """获取从指定状态可转移的目标状态集合"""
        transitions = {
            # 基础状态
            State.IDLE: {State.INTERLUDE, State.SPLASH, State.BLANK},
            State.SPLASH: {State.IDLE, State.INTERLUDE},
            State.BLANK: {State.IDLE, State.INTERLUDE, State.ENTRY},

            State.INTERLUDE: {
                State.ENTRY, State.SONGSEL, State.PLAY, State.MODESEL,
                State.PAY, State.BRANK, State.ARANK, State.DANSCORE,
                State.IDLE, State.BLANK, State.OTHERS,
                State.DANSEL, State.AWAIT, State.BWAIT,  # 模式选择入口
                State.CONFIRM, State.ACONFIRM,  # 可能跳过选曲直接确认
            },

            State.ENTRY: {State.INTERLUDE, State.MODESEL, State.BLANK},
            State.MODESEL: {State.PAY, State.INTERLUDE, State.ENTRY},
            State.PAY: {State.INTERLUDE, State.MODESEL, State.ENTRY},

            # 选曲/确认
            State.SONGSEL: {State.INTERLUDE, State.CONFIRM, State.PLAY, State.PLAY1, State.PLAY2, State.PLAY12, State.PLAYD, State.ENTRY},
            State.CONFIRM: {State.PLAY, State.PLAY1, State.PLAY2, State.PLAY12, State.PLAYD, State.SONGSEL, State.INTERLUDE, State.ENTRY},

            # 【曲目进程】- 所有 play 状态具有相同的转移规则
            State.PLAY: {State.DEATH, State.SCORE, State.INTERLUDE, State.ENTRY},
            State.PLAY1: {State.DEATH, State.SCORE, State.INTERLUDE, State.ENTRY},
            State.PLAY2: {State.DEATH, State.SCORE, State.INTERLUDE, State.ENTRY},
            State.PLAY12: {State.DEATH, State.SCORE, State.INTERLUDE, State.ENTRY},
            State.PLAYD: {State.DEATH, State.SCORE, State.INTERLUDE, State.ENTRY},
            State.DEATH: {State.PLAY, State.PLAY1, State.PLAY2, State.PLAY12, State.PLAYD, State.INTERLUDE, State.SCORE, State.DANSCORE, State.ENTRY},
            State.SCORE: {State.INTERLUDE, State.SONGSEL, State.ENTRY},

            # BPL Battle
            State.BWAIT: {State.INTERLUDE, State.BSEL, State.ENTRY},
            State.BSEL: {State.INTERLUDE, State.CONFIRM, State.BWAIT},
            State.BRANK: {State.INTERLUDE, State.IDLE, State.ENTRY},

            # Arena
            State.AWAIT: {State.INTERLUDE, State.SONGSEL, State.ENTRY},
            State.ACONFIRM: {State.CONFIRM, State.SONGSEL, State.INTERLUDE},
            State.ASUM: {State.ARANK, State.INTERLUDE},
            State.ARANK: {State.INTERLUDE, State.IDLE, State.ENTRY},

            # Dan
            State.DANSEL: {State.CONFIRM, State.INTERLUDE, State.ENTRY},
            State.DANSCORE: {State.INTERLUDE, State.IDLE, State.ENTRY},

            # 其他
            State.LAB: {State.IDLE, State.INTERLUDE, State.ENTRY},
            State.OTHERS: {State.IDLE, State.INTERLUDE, State.ENTRY},
            State.SET: {State.IDLE, State.INTERLUDE, State.ENTRY},
        }
        return transitions.get(state, {State.IDLE, State.INTERLUDE, State.ENTRY})

    def _update_context(self, from_state: State, to_state: State):
        """更新游戏上下文"""
        # 模式检测：从 interlude 转移出时根据目标状态确定模式
        if from_state == State.INTERLUDE and self._context.mode == GameMode.UNKNOWN:
            if to_state in (State.SONGSEL, State.CONFIRM):
                self._context.mode = GameMode.STANDARD
                logger.info("Mode detected: STANDARD")
            elif to_state in (State.BWAIT, State.BSEL):
                self._context.mode = GameMode.BPL_BATTLE
                logger.info("Mode detected: BPL_BATTLE")
            elif to_state in (State.AWAIT, State.ACONFIRM):
                self._context.mode = GameMode.ARENA
                logger.info("Mode detected: ARENA")
            elif to_state == State.DANSEL:
                self._context.mode = GameMode.DAN
                logger.info("Mode detected: DAN")

        # 处理 entry 状态：上机（开始游戏）或下机（结束游戏）
        if to_state == State.ENTRY:
            # 从结算/游戏相关状态进入 entry = 玩家下机，游戏结束
            if from_state in (State.SCORE, State.BRANK, State.ARANK, State.DANSCORE,
                               State.DEATH, State.INTERLUDE) and self._context.game_active:
                self._context.game_active = False
                logger.info("Player exit detected - game session ended")
            # 从其他状态进入 entry = 玩家上机，开始新游戏
            elif not self._context.game_active and from_state not in (State.MODESEL, State.PAY):
                self._context.reset()
                logger.info("Player entry detected - new game session started")

        # 追踪【曲目进程】
        if to_state.is_play_state():
            self._context.in_song_cycle = True
            self._context.game_active = True  # 确认游戏进行中

            # 检测是否为快捷重启（standard 模式下）
            if (self._context.mode == GameMode.STANDARD and
                from_state in (State.DEATH, State.SCORE)):
                # 快捷重启：增加尝试次数，不增加歌曲数
                self._context.try_count += 1
                logger.info(f"Song {self._context.song_count} retry #{self._context.try_count} (quick restart)")
            elif from_state == State.INTERLUDE and not self._context._last_song_completed:
                # 从 interlude 进入 play 且上一首未完成（可能是死亡后直接下一首）
                self._context.song_count += 1
                self._context.try_count = 1
                self._context._last_song_completed = False
                logger.info(f"Song {self._context.song_count} started (from interlude)")
            else:
                # 正常新曲开始
                self._context.song_count += 1
                self._context.try_count = 1
                self._context._last_song_completed = False
                logger.info(f"Song {self._context.song_count} started (try #{self._context.try_count})")

        # 快捷重启检测：从 play 状态到 play 状态（模式切换）
        if from_state.is_play_state() and to_state.is_play_state():
            # play 状态之间的转换，记录为同曲尝试
            if self._context.mode == GameMode.STANDARD and self._context.in_song_cycle:
                logger.debug(f"Play mode transition: {from_state.value} -> {to_state.value}")

        # 检测死亡
        if to_state == State.DEATH:
            self._context.death_occurred = True

        # 【曲目进程】结束 - 标记歌曲已完成
        if from_state == State.SCORE and to_state == State.INTERLUDE:
            self._context.in_song_cycle = False
            self._context._last_song_completed = True
            logger.info(f"Song {self._context.song_count} completed (score shown)")

        # # 从 DEATH 直接到 INTERLUDE（未显示成绩）
        # if from_state == State.DEATH and to_state == State.INTERLUDE:
        #     self._context.in_song_cycle = False
        #     self._context._last_song_completed = False
        #     logger.info(f"Song {self._context.song_count} ended with death (no score)")

        # Dan 模式特殊处理：death 后跳出循环
        if self._context.mode == GameMode.DAN and to_state == State.DEATH:
            self._context.in_song_cycle = False

        # 机器空闲判定：entry -> blank 表示玩家下机，机器回到空闲
        if from_state == State.ENTRY and to_state == State.BLANK:
            self._context.game_active = False
            self._context.reset()
            logger.info("Machine idle detected: player exited to blank screen")

    def _default_transition_handler(self, from_state: State, to_state: State, context: StateContext):
        """默认状态转移处理函数 - 输出到控制台"""
        mode_str = context.mode.name if context.mode != GameMode.UNKNOWN else "UNKNOWN"
        song_info = f"[Song {context.song_count}.{context.try_count}]" if context.in_song_cycle else ""
        idle_mark = "[IDLE]" if not context.game_active and to_state == State.BLANK else ""

        print(f"[STATE] {from_state.value:12} -> {to_state.value:12} | Mode: {mode_str:10} {song_info} {idle_mark}")

        # 场景切换建议（预留 OBS 集成点）
        scene = self._get_obs_scene(to_state)
        if scene:
            print(f"[OBS] Switch to scene: {scene}")

    def _get_obs_scene(self, state: State) -> Optional[str]:
        """根据状态获取 OBS 场景名称"""
        scene_map = {
            State.IDLE: "待机画面",
            State.SPLASH: "待机画面",
            State.BLANK: "过渡画面",
            State.INTERLUDE: "过渡画面",
            State.ENTRY: "准备画面",
            State.MODESEL: "准备画面",
            State.PAY: "准备画面",
            State.SONGSEL: "选曲画面",
            State.CONFIRM: "选曲画面",
            State.ACONFIRM: "选曲画面",
            State.PLAY: "游戏画面",
            State.DEATH: "失败画面",
            State.SCORE: "成绩画面",
            State.BRANK: "结算画面",
            State.ARANK: "结算画面",
            State.DANSCORE: "结算画面",
            State.DANSEL: "准备画面",
            State.BWAIT: "准备画面",
            State.AWAIT: "准备画面",
            State.BSEL: "选曲画面",
            State.ASUM: "成绩画面",
        }
        return scene_map.get(state)

    def get_status(self) -> dict:
        """获取状态机当前状态摘要"""
        return {
            "state": self._state.value,
            "mode": self._context.mode.name,
            "song_count": self._context.song_count,
            "try_count": self._context.try_count,
            "in_song_cycle": self._context.in_song_cycle,
            "death_occurred": self._context.death_occurred,
            "game_active": self._context.game_active,
            "machine_idle": not self._context.game_active,
            "history_length": len(self._transition_history),
        }


class IIDXStateMachineWithOBS(IIDXStateMachine):
    """
    带 OBS 集成的状态机（预留实现）

    后续实现 OBS WebSocket 通信，实际切换场景
    """

    def __init__(self, obs_host: str = "localhost", obs_port: int = 4455, **kwargs):
        super().__init__(**kwargs)
        self.obs_host = obs_host
        self.obs_port = obs_port
        self._obs_connected = False

    def _default_transition_handler(self, from_state: State, to_state: State, context: StateContext):
        """OBS 场景切换处理"""
        super()._default_transition_handler(from_state, to_state, context)

        # TODO: 实现 OBS WebSocket 调用
        scene = self._get_obs_scene(to_state)
        if scene and self._obs_connected:
            # self._switch_obs_scene(scene)
            pass

    def connect_obs(self) -> bool:
        """连接 OBS WebSocket（预留）"""
        # TODO: 使用 obs-websocket-py 或 simpleobsws 连接
        logger.info(f"Connecting to OBS at {self.obs_host}:{self.obs_port}...")
        self._obs_connected = True  # Placeholder
        return self._obs_connected

    def disconnect_obs(self):
        """断开 OBS 连接（预留）"""
        self._obs_connected = False
        logger.info("Disconnected from OBS")

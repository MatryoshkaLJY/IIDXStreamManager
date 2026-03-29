"""配置管理"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class StateMachineConfig:
    """状态机配置"""
    debounce_frames: int = 2           # 防抖帧数
    enable_obs: bool = False           # 是否启用 OBS 集成
    obs_host: str = "localhost"        # OBS WebSocket 地址
    obs_port: int = 4455               # OBS WebSocket 端口
    obs_password: Optional[str] = None # OBS WebSocket 密码


@dataclass
class SceneMapping:
    """OBS 场景映射配置"""
    idle: str = "待机画面"
    interlude: str = "过渡画面"
    entry: str = "准备画面"
    modesel: str = "准备画面"
    pay: str = "准备画面"
    songsel: str = "选曲画面"
    confirm: str = "选曲画面"
    aconfirm: str = "选曲画面"
    play: str = "游戏画面"
    death: str = "失败画面"
    score: str = "成绩画面"
    brank: str = "结算画面"
    arank: str = "结算画面"
    danscore: str = "结算画面"

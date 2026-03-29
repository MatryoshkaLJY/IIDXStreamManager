"""IIDX Stream State Machine"""

from .config import SceneMapping, StateMachineConfig
from .state_machine import (
    GameMode,
    IIDXStateMachine,
    IIDXStateMachineWithOBS,
    State,
    StateContext,
    StateTransitionCallback,
)

__version__ = "0.1.0"
__all__ = [
    "IIDXStateMachine",
    "IIDXStateMachineWithOBS",
    "State",
    "GameMode",
    "StateContext",
    "StateTransitionCallback",
    "StateMachineConfig",
    "SceneMapping",
]

"""向两个 scoreboard 推送数据（WS 8080 BPL / 8081 淘汰赛）。

协议已对照两边 app.js 验证：
- BPL init 的 matches 项字段为 type/leftPlayers/rightPlayers/theme；
- 淘汰赛决赛的 score/settle 中 group 必须为 "finals"（"final" 会静默丢 DOM 更新）。
传输为每次推送一次短连接，简单可靠；推送失败抛 PushError，由调用方决定重试/报错。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import websockets

from ..config.models import KnockoutConfig, TeamMatchConfig

DEFAULT_URIS = {
    "bpl": "ws://localhost:8080",
    "knockout": "ws://localhost:8081",
}


class PushError(Exception):
    """推送失败（连接失败/发送异常）。"""


# ---- 载荷构造（纯函数） ----

def bpl_init_payload(config: TeamMatchConfig) -> dict[str, Any]:
    def team_data(team) -> dict[str, Any]:
        colors = {"primary": team.colors.primary, "secondary": team.colors.secondary}
        if team.colors.accent:
            colors["accent"] = team.colors.accent
        return {"name": team.name, "logo": team.emoji, "colors": colors}

    return {
        "cmd": "init",
        "data": {
            "stageName": config.stage_name,
            "matchNumber": config.match_number,
            "leftTeam": team_data(config.left_team),
            "rightTeam": team_data(config.right_team),
            "matches": [
                {
                    "type": rnd.type,
                    "leftPlayers": list(rnd.left_players),
                    "rightPlayers": list(rnd.right_players),
                    "theme": rnd.theme,
                }
                for rnd in config.rounds
            ],
        },
    }


def bpl_reset_payload() -> dict[str, Any]:
    return {"cmd": "reset"}


def knockout_init_payload(config: KnockoutConfig) -> dict[str, Any]:
    return {
        "cmd": "init",
        "data": {
            "tournamentName": config.tournament_name,
            "groups": {g: list(config.groups[g]) for g in ("A", "B", "C", "D")},
        },
    }


def knockout_reset_payload() -> dict[str, Any]:
    return {"cmd": "reset"}


# ---- 传输 ----

async def _send(uri: str, payload: dict[str, Any], timeout: float) -> None:
    async with websockets.connect(uri, open_timeout=timeout) as ws:
        await ws.send(json.dumps(payload, ensure_ascii=False))


class ScoreboardPusher:
    def __init__(self, uris: dict[str, str] | None = None, timeout: float = 5.0) -> None:
        self.uris = dict(DEFAULT_URIS if uris is None else uris)
        self.timeout = timeout

    def push(self, board: str, payload: dict[str, Any]) -> None:
        uri = self.uris.get(board)
        if not uri:
            raise PushError(f"未知记分板: {board!r}")
        try:
            asyncio.run(_send(uri, payload, self.timeout))
        except (OSError, websockets.WebSocketException, asyncio.TimeoutError) as exc:
            raise PushError(f"推送到 {board} ({uri}) 失败: {exc}") from exc

    def push_all(self, items: list[dict[str, Any]]) -> None:
        """按顺序推送 session.confirm 产出的载荷列表，任一失败即抛错中止。"""
        for item in items:
            self.push(item["board"], item["payload"])

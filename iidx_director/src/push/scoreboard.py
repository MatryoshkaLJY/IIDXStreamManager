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

from ..config.models import KnockoutConfig, KnockoutEFConfig, KnockoutFinalConfig, TeamMatchConfig

# 用 127.0.0.1 而非 localhost，理由同 push/overlay.py（::1 无监听时连接会白等约 2 秒）。
DEFAULT_URIS = {
    "bpl": "ws://127.0.0.1:8080",
    "knockout": "ws://127.0.0.1:8081",
}


class PushError(Exception):
    """推送失败（连接失败/发送异常）。"""


# ---- 载荷构造（纯函数） ----

def bpl_init_payload(
    config: TeamMatchConfig, initial_left: int = 0, initial_right: int = 0
) -> dict[str, Any]:
    def team_data(team) -> dict[str, Any]:
        colors = {"primary": team.colors.primary, "secondary": team.colors.secondary}
        if team.colors.accent:
            colors["accent"] = team.colors.accent
        return {"name": team.name, "logo": team.emoji, "colors": colors}

    def round_theme(rnd) -> str:
        if rnd.theme:
            return rnd.theme
        themes = [g.theme for g in rnd.games if g.theme]
        return " / ".join(themes) if themes else ""

    return {
        "cmd": "init",
        "data": {
            "stageName": config.stage_name,
            "matchNumber": config.match_number,
            "leftTeam": team_data(config.left_team),
            "rightTeam": team_data(config.right_team),
            # 抢夺赛（前 grab_rounds 回合）不上计分板，其 PT 通过初始分录入
            "initialLeftScore": int(initial_left),
            "initialRightScore": int(initial_right),
            "matches": [
                {
                    "type": rnd.type,
                    "leftPlayers": list(dict.fromkeys(p for g in rnd.games for p in g.left_players)),
                    "rightPlayers": list(dict.fromkeys(p for g in rnd.games for p in g.right_players)),
                    "theme": round_theme(rnd),
                }
                for rnd in config.rounds[config.grab_rounds :]
            ],
        },
    }


def bpl_reset_payload() -> dict[str, Any]:
    return {"cmd": "reset"}


def knockout_init_payload(config: KnockoutConfig | KnockoutEFConfig | KnockoutFinalConfig) -> dict[str, Any]:
    """淘汰赛 init 载荷。16 人赛推 A-D 四组；8 人 EF 赛制推 E/F 两组、4 人决赛赛制
    推 finals 一组，并带 startGroup 标记，记分板据此隐藏前置阶段区域并直接从
    起始组起播。"""
    groups = {
        g: list(config.groups[g])
        for g in ("A", "B", "C", "D", "E", "F", "finals")
        if g in config.groups
    }
    data: dict[str, Any] = {
        "tournamentName": config.tournament_name,
        "groups": groups,
    }
    if "finals" in groups:
        data["startGroup"] = "finals"
    elif not any(g in groups for g in ("A", "B", "C", "D")):
        data["startGroup"] = "E"
    return {"cmd": "init", "data": data}


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

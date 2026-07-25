"""场景信息推送（WS 8082，OBS 浏览器源）。

定义场景信息 JSON 协议并推送到 sceneinfo relay。overlay.html 消费现有
回合消息，并额外支持 PSD 文字图层的模板和字段覆盖。

协议：
- round_start:  回合开始（对阵、队名/颜色、机台分配）
- round_result: 回合结果（各选手 EX、判定）
- match_end:    比赛结束
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import websockets

from ..match.session import MatchSession

DEFAULT_URI = "ws://localhost:8082"
TEMPLATES = {"dp_arena", "dp_bpl", "sp_arena", "sp_bpl", "live"}


def template_for_scene(scene: str | None, mode: str) -> str:
    """Map an OBS scene name to one of the PSD-derived overlay templates."""
    name = (scene or "").lower()
    if "现场" in (scene or "") or "live" in name:
        return "live"
    is_dp = "dp" in name or "双" in (scene or "")
    if mode == "team":
        return "dp_bpl" if is_dp else "sp_bpl"
    return "dp_arena" if is_dp else "sp_arena"


def _text_values(session: MatchSession) -> dict[str, str]:
    info = session.current_round_info()
    values: dict[str, str] = {
        "header_round": f"ROUND {info.get('round_no', 1)}",
    }
    if info.get("theme"):
        values["header_theme"] = str(info["theme"])
    if info.get("left_team"):
        values["left_team_name"] = str(info["left_team"])
    if info.get("right_team"):
        values["right_team_name"] = str(info["right_team"])
    if info.get("left_players"):
        values["left_player"] = " / ".join(info["left_players"])
    if info.get("right_players"):
        values["right_player"] = " / ".join(info["right_players"])
    for player, slot in session.assignments.items():
        match = re.search(r"([1-4])", str(slot.get("machine", "")))
        if match:
            values[f"machine_{match.group(1)}_player"] = player
    result = session.last_result or {}
    if result.get("left_points") is not None:
        values["left_points"] = f"{result['left_points']}PT"
    if result.get("right_points") is not None:
        values["right_points"] = f"{result['right_points']}PT"
    return values


# ---- 载荷构造（纯函数） ----

def round_start_payload(session: MatchSession, template: str | None = None) -> dict[str, Any]:
    info = session.current_round_info()
    entries = []
    for player, slot in session.assignments.items():
        entry: dict[str, Any] = {
            "player": player,
            "machine": slot["machine"],
            "side": slot["side"],
            "team": None,
            "color": None,
        }
        if session.mode == "team":
            cfg = session.config
            if player in cfg.left_team.players:
                entry["team"] = cfg.left_team.name
                entry["color"] = cfg.left_team.colors.primary
            elif player in cfg.right_team.players:
                entry["team"] = cfg.right_team.name
                entry["color"] = cfg.right_team.colors.primary
        entries.append(entry)
    data = {
        "mode": session.mode,
        "round": info,
        "entries": entries,
        "texts": _text_values(session),
    }
    if template in TEMPLATES:
        data["template"] = template
    return {"cmd": "round_start", "data": data}


def round_result_payload(session: MatchSession, template: str | None = None) -> dict[str, Any]:
    data = {
        "cmd": "round_result",
        "data": {
            "mode": session.mode,
            "round": session.current_round_info(),
            "result": session.last_result,
            "texts": _text_values(session),
        },
    }
    if template in TEMPLATES:
        data["data"]["template"] = template
    return data


def match_end_payload(session: MatchSession, template: str | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {"mode": session.mode}
    if session.mode == "team":
        data["rounds"] = session.team_round_results
    elif session.tournament is not None:
        data["final_ranking"] = session.tournament.final_ranking
    if template in TEMPLATES:
        data["template"] = template
    return {"cmd": "match_end", "data": data}


# ---- 传输 ----

async def _send(uri: str, payload: dict[str, Any], timeout: float) -> None:
    async with websockets.connect(uri, open_timeout=timeout) as ws:
        await ws.send(json.dumps(payload, ensure_ascii=False))


class SceneInfoPusher:
    """场景信息推送失败不阻断主流程（smoke test 通道），仅返回 False。"""

    def __init__(self, uri: str = DEFAULT_URI, timeout: float = 3.0) -> None:
        self.uri = uri
        self.timeout = timeout

    def push(self, payload: dict[str, Any]) -> bool:
        try:
            asyncio.run(_send(self.uri, payload, self.timeout))
            return True
        except (OSError, websockets.WebSocketException, asyncio.TimeoutError):
            return False

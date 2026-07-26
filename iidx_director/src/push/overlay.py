"""OBS overlay 推送（WS 8082，OBS 浏览器源）。

定义 overlay JSON 协议并推送到 overlay relay。obs-overlay.html 消费回合消息，
并将语义化文字和 Hue 映射到固定布局。

协议：
- round_start:  回合开始（对阵、队名/颜色、机台分配）
- round_result: 回合结果（各选手 EX、判定）
- match_end:    比赛结束
"""

from __future__ import annotations

import asyncio
import colorsys
import json
import re
import uuid
from typing import Any

import websockets

from ..match.session import MatchSession

DEFAULT_URI = "ws://localhost:8082"
TEMPLATES = {"dp_arena", "dp_bpl", "sp_arena", "sp_bpl", "live"}


def template_for_scene(scene: str | None, mode: str) -> str:
    """Map an OBS scene name to one of the bundled overlay presets."""
    raw_scene = str(scene or "").strip()
    name = raw_scene.lower().replace(" ", "").replace("_", "").replace("-", "")
    if name in {"scoreboardweb", "scoreboard"}:
        return "live"
    if "现场" in raw_scene or "live" in name:
        return "live"
    is_dp = "dp" in name or "双" in (scene or "")
    if "个人" in raw_scene:
        return "dp_arena" if is_dp else "sp_arena"
    if name in {"spbpl", "dpbpl"}:
        return "dp_bpl" if is_dp else "sp_bpl"
    if name in {"sparena", "dparena"}:
        return "dp_arena" if is_dp else "sp_arena"
    if "2v2" in name:
        return "dp_arena" if is_dp else "sp_arena"
    if "1v1" in name:
        return "dp_bpl" if is_dp else "sp_bpl"
    if mode == "team":
        # Backward-compatible names used by older runtime state files.
        return "dp_bpl" if is_dp else "sp_bpl"
    return "dp_arena" if is_dp else "sp_arena"


def hue_for_color(value: str | None) -> float:
    """Convert a hex color to the hue-rotate angle used by the red boards."""
    raw = str(value or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(char * 2 for char in raw)
    if len(raw) != 6:
        return 0.0
    try:
        red, green, blue = (int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return 0.0
    hue, saturation, _ = colorsys.rgb_to_hsv(red, green, blue)
    return round(hue * 360, 3) if saturation > 0.01 else 0.0


def _text_values(session: MatchSession, template: str | None = None) -> dict[str, str]:
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


def _hue_values(session: MatchSession, template: str | None = None) -> dict[str, float]:
    if session.mode != "team":
        return {
            "machine_1": 0.0,
            "machine_2": 60.0,
            "machine_3": 120.0,
            "machine_4": 240.0,
        }
    if not template or template == "live":
        return {}
    config = session.config
    left_hue = hue_for_color(config.left_team.colors.primary)
    right_hue = hue_for_color(config.right_team.colors.primary)
    if template and template.endswith("_arena"):
        # Arena has one background board per cabinet, so derive each board's
        # team color from the assignment rather than using BPL's left/right keys.
        info = session.current_round_info()
        left_players = set(config.left_team.players) | set(info.get("left_players", []))
        right_players = set(config.right_team.players) | set(info.get("right_players", []))
        hues: dict[str, float] = {}
        for player, slot in session.assignments.items():
            match = re.search(r"([1-4])", str(slot.get("machine", "")))
            if not match:
                continue
            if player in left_players:
                hues[f"machine_{match.group(1)}"] = left_hue
            elif player in right_players:
                hues[f"machine_{match.group(1)}"] = right_hue
        return hues
    return {"left": left_hue, "right": right_hue}


# ---- 载荷构造（纯函数） ----

def round_start_payload(
    session: MatchSession, template: str | None = None, scene: str | None = None
) -> dict[str, Any]:
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
        "texts": _text_values(session, template),
        "hues": _hue_values(session, template),
    }
    if template in TEMPLATES:
        data["template"] = template
    if scene:
        data["scene"] = scene
    return {"cmd": "round_start", "data": data}


def round_result_payload(
    session: MatchSession, template: str | None = None, scene: str | None = None
) -> dict[str, Any]:
    data = {
        "cmd": "round_result",
        "data": {
            "mode": session.mode,
            "round": session.current_round_info(),
            "result": session.last_result,
            "texts": _text_values(session, template),
            "hues": _hue_values(session, template),
        },
    }
    if template in TEMPLATES:
        data["data"]["template"] = template
    if scene:
        data["data"]["scene"] = scene
    return data


def match_end_payload(
    session: MatchSession, template: str | None = None, scene: str | None = None
) -> dict[str, Any]:
    data: dict[str, Any] = {"mode": session.mode}
    if session.mode == "team":
        data["rounds"] = session.team_round_results
    elif session.tournament is not None:
        data["final_ranking"] = session.tournament.final_ranking
    if template in TEMPLATES:
        data["template"] = template
    if scene:
        data["scene"] = scene
    return {"cmd": "match_end", "data": data}


# ---- 传输 ----

async def _send(uri: str, payload: dict[str, Any], timeout: float) -> None:
    async with websockets.connect(uri, open_timeout=timeout) as ws:
        await ws.send(json.dumps(payload, ensure_ascii=False))


class OverlayPusher:
    """Overlay 推送失败不阻断主流程，仅返回 False。"""

    def __init__(self, uri: str = DEFAULT_URI, timeout: float = 3.0) -> None:
        self.uri = uri
        self.timeout = timeout

    def push(self, payload: dict[str, Any]) -> bool:
        try:
            asyncio.run(_send(self.uri, payload, self.timeout))
            return True
        except (OSError, websockets.WebSocketException, asyncio.TimeoutError):
            return False

    def command(self, payload: dict[str, Any], *, require_ack: bool = True) -> bool:
        """Send a relay command and optionally wait for browser acknowledgement.

        Older/fake relays do not implement ``recv``; treating a successful send
        as success keeps the existing fire-and-forget protocol compatible.
        """
        message = dict(payload)
        request_id = message.setdefault("request_id", uuid.uuid4().hex)

        async def send_and_wait() -> bool:
            async with websockets.connect(self.uri, open_timeout=self.timeout) as ws:
                await ws.send(json.dumps(message, ensure_ascii=False))
                if not require_ack or not hasattr(ws, "recv"):
                    return True
                deadline = asyncio.get_running_loop().time() + self.timeout
                while True:
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        return False
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                    except (AttributeError, asyncio.TimeoutError):
                        return False
                    try:
                        ack = json.loads(raw)
                    except (TypeError, json.JSONDecodeError):
                        continue
                    if ack.get("request_id") != request_id:
                        continue
                    return bool(ack.get("ok", False))

        try:
            return asyncio.run(send_and_wait())
        except (OSError, websockets.WebSocketException, asyncio.TimeoutError):
            return False

    def stage(self, scene: str, snapshot: dict[str, Any]) -> bool:
        return self.command({"cmd": "stage", "scene": scene, "snapshot": snapshot})

    def activate(self, scene: str) -> bool:
        return self.command({"cmd": "activate", "scene": scene})

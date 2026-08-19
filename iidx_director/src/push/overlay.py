"""OBS overlay 推送（WS 8082，OBS 浏览器源）。

定义 overlay JSON 协议并推送到 overlay relay。obs-overlay.html 消费回合消息，
并将语义化文字和 Hue 映射到固定布局。

协议：
- round_start:  回合开始（对阵、队名/颜色、机台分配）
- round_result: 回合结果（各选手 EX、判定）
- match_end:    比赛结束
- set_text:     导播在 prep 页手动微调文字
- set_hue:      导播在 prep 页手动微调背景 Hue
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from typing import Any

import websockets

from ..match.session import MatchSession, SessionPhase

# 注意用 127.0.0.1 而非 localhost：本机 ::1 上无监听时 SYN 被静默丢弃，
# asyncio 顺序尝试地址，"localhost" 解析到 ::1 会让每次连接白等约 2 秒。
DEFAULT_URI = "ws://127.0.0.1:8082"
TEMPLATES = {"dp_arena", "dp_bpl", "sp_arena", "sp_bpl", "live"}


def template_for_scene(scene: str | None, mode: str) -> str:
    """Map an OBS scene name to one of the bundled overlay presets."""
    raw_scene = str(scene or "").strip()
    name = raw_scene.lower().replace(" ", "").replace("_", "").replace("-", "")
    if "scoreboard" in name:
        return "live"
    if "grid" in name:
        # Grid 多画面场景不叠加比赛 overlay
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


def _text_values(
    session: MatchSession,
    template: str | None = None,
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    info = session.current_round_info()
    values: dict[str, str] = {
        "header_round": f"ROUND {info.get('round_no', 1)}",
    }
    # 题头根据比赛模式和游玩类型动态生成，避免团队赛 2v2 使用 arena 模板时仍显示“个人赛”。
    is_dp = session.play_type == "DP"
    if session.mode == "team":
        values["header_match_type"] = "DP团队赛" if is_dp else "SP团队赛"
    else:
        values["header_match_type"] = "DP个人赛" if is_dp else "SP个人赛"
    if template and template.endswith("_arena"):
        # Arena 题头只显示 ROUND X，不显示主题；显式发空串清掉前端占位文字
        values["header_theme"] = ""
    elif info.get("theme"):
        theme = str(info["theme"])
        if info.get("grab"):
            # 抢夺赛只显示 LEVEL X（配合 header_round 的 ROUND X），长主题文字会溢出文本框
            level = re.search(r"LEVEL\s*(\d+)", theme, re.IGNORECASE)
            theme = f"LEVEL {level.group(1)}" if level else theme
        elif info.get("tiebreaker"):
            theme = f"加赛　{theme}"
        # 正赛只显示 ROUND X + 主题，不加“第 x/N 局”前缀，避免溢出文本框
        values["header_theme"] = theme
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
    if session.mode == "team":
        # 团队赛显示累计队伍总分：已结束回合 + 当前回合已确认局 + REVIEW 中待确认局。
        # 抢夺赛初始 PT 录入后按计分板口径（初始 PT + 正赛回合），否则含抢夺赛胜场累计。
        finished = session.team_round_results
        if session.initial_scores is not None:
            finished = [r for r in finished if not r.get("grab")]
            left_total = session.initial_scores["left"]
            right_total = session.initial_scores["right"]
        else:
            left_total = right_total = 0
        left_total += sum(r["left_points"] for r in finished) + sum(
            r["left_points"] for r in session.game_results
        )
        right_total += sum(r["right_points"] for r in finished) + sum(
            r["right_points"] for r in session.game_results
        )
        if result and session.phase == SessionPhase.REVIEW:
            left_total += result.get("left_points", 0)
            right_total += result.get("right_points", 0)
        values["left_points"] = f"{left_total}PT"
        values["right_points"] = f"{right_total}PT"
    else:
        if result.get("left_points") is not None:
            values["left_points"] = f"{result['left_points']}PT"
        if result.get("right_points") is not None:
            values["right_points"] = f"{result['right_points']}PT"
    if overrides:
        values.update(overrides)
    return values


# 名板素材为红色，hue-rotate 240° 转蓝、0° 保持红色
HUE_BLUE = 240.0
HUE_RED = 0.0


def _hue_values(
    session: MatchSession,
    template: str | None = None,
    overrides: dict[str, float] | None = None,
) -> dict[str, float]:
    if session.mode != "team":
        # 个人赛 overlay 统一红色；显式发 0.0 以覆盖前端缓存的旧 Hue
        hues = {
            "machine_1": HUE_RED,
            "machine_2": HUE_RED,
            "machine_3": HUE_RED,
            "machine_4": HUE_RED,
        }
    elif not template or template == "live":
        hues = {}
    else:
        if template and template.endswith("_arena"):
            # Arena has one background board per cabinet, so derive each board's
            # team color from the assignment rather than using BPL's left/right keys.
            config = session.config
            info = session.current_round_info()
            left_players = set(config.left_team.players) | set(info.get("left_players", []))
            right_players = set(config.right_team.players) | set(info.get("right_players", []))
            hues = {}
            for player, slot in session.assignments.items():
                match = re.search(r"([1-4])", str(slot.get("machine", "")))
                if not match:
                    continue
                if player in left_players:
                    hues[f"machine_{match.group(1)}"] = HUE_BLUE
                elif player in right_players:
                    hues[f"machine_{match.group(1)}"] = HUE_RED
        else:
            # BPL overlay 固定左蓝右红，不再使用队伍配置色
            hues = {"left": HUE_BLUE, "right": HUE_RED}
    if overrides:
        hues.update(overrides)
    return hues


# ---- 载荷构造（纯函数） ----

def round_start_payload(
    session: MatchSession,
    template: str | None = None,
    scene: str | None = None,
    text_overrides: dict[str, str] | None = None,
    hue_overrides: dict[str, float] | None = None,
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
        "texts": _text_values(session, template, text_overrides),
        "hues": _hue_values(session, template, hue_overrides),
    }
    if template in TEMPLATES:
        data["template"] = template
    if scene:
        data["scene"] = scene
    return {"cmd": "round_start", "data": data}


def round_result_payload(
    session: MatchSession,
    template: str | None = None,
    scene: str | None = None,
    text_overrides: dict[str, str] | None = None,
    hue_overrides: dict[str, float] | None = None,
) -> dict[str, Any]:
    data = {
        "cmd": "round_result",
        "data": {
            "mode": session.mode,
            "round": session.current_round_info(),
            "result": session.last_result,
            "texts": _text_values(session, template, text_overrides),
            "hues": _hue_values(session, template, hue_overrides),
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


def set_text_payload(values: dict[str, str]) -> dict[str, Any]:
    """导播网页手动覆盖 overlay 文字。"""
    return {"cmd": "set_text", "data": {"values": values}}


def set_hue_payload(values: dict[str, float]) -> dict[str, Any]:
    """导播网页手动覆盖 overlay 背景 Hue。"""
    return {"cmd": "set_hue", "data": {"values": values}}


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

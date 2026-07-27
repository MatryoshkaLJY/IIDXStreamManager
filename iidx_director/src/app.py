"""iidx_director Web 应用（Flask + Flask-SocketIO，端口 5003）。

薄路由层：所有比赛逻辑在 match/ 会话中，I/O（OBS / WebSocket）在这里编排。
API 约定：永远返回 HTTP 200 + {"success": bool, "error": str?}。
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import threading
import time
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file, send_from_directory
from flask_socketio import SocketIO

from .config import loader
from .config.loader import ConfigError
from .match.session import MatchSession, SessionError, SessionPhase
from .obs.client import OBSClient
from .obs.monitor import CabinetMonitor
from .push.overlay import (
    OverlayPusher,
    match_end_payload,
    round_result_payload,
    round_start_payload,
    template_for_scene,
)
from .push.scoreboard import (
    PushError,
    ScoreboardPusher,
    bpl_init_payload,
    bpl_reset_payload,
    knockout_init_payload,
    knockout_reset_payload,
)
from .state import RuntimeState, load_runtime_state, save_runtime_state
from .scene import PendingError, SceneCoordinator
from .services import DependencyManager
from .screenshots import EMPTY_SCREENSHOT_PNG, ScreenshotStore, round_key_for_session

logger = logging.getLogger(__name__)

WEB_PORT = 5003
SCOREBOARD_SETTLE_SECONDS = 5.0
MONOREPO_ROOT = Path(__file__).resolve().parents[2]


class AppContext:
    """持有全部运行时对象（替代旧应用散落的全局变量）。"""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.state: RuntimeState = load_runtime_state()
        if os.environ.get("IIDX_TEST_MODE", "").strip().lower() in {"1", "true", "yes", "on"}:
            self.state.test_mode = True
        self.config_dir = config_dir or loader.CONFIG_DIR
        loader.ensure_templates(self.config_dir)
        self.obs_password: str | None = os.environ.get("IIDX_OBS_PASSWORD")
        self.obs: OBSClient | None = None
        self.monitor: CabinetMonitor | None = None
        self.scoreboard = ScoreboardPusher()
        self.overlay = OverlayPusher()
        self.session: MatchSession | None = None
        self.scene_template: str | None = None
        self.scenes = SceneCoordinator(self.state.scenes)
        self.current_scene: str | None = None
        self.screenshots = ScreenshotStore()
        self.sleep = time.sleep
        self.lock = threading.RLock()

    # ---- OBS ----

    def obs_connected(self) -> bool:
        return self.obs is not None and self.obs.connected

    def connect_obs(self, host: str, port: int, password: str | None) -> None:
        client = OBSClient(host=host, port=port, password=password)
        client.connect()
        if self.obs is not None:
            self.obs.disconnect()
        self.obs = client
        self.obs_password = password
        self.state.obs_host = host
        self.state.obs_port = port
        save_runtime_state(self.state)

    def try_switch_scene(self, scene: str | None, warnings: list[str]) -> bool:
        """切场景失败只记警告，不阻断流程。"""
        if not scene:
            return False
        if not self.obs_connected():
            warnings.append("OBS 未连接，未切换场景")
            return False
        try:
            self.obs.switch_scene(scene)  # type: ignore[union-attr]
            return True
        except Exception as exc:
            warnings.append(f"切换场景 {scene} 失败: {exc}")
            return False

    def apply_match_visibility(self, scene: str, session: MatchSession) -> None:
        if not self.obs_connected():
            raise RuntimeError("OBS 未连接")
        team_by_player: dict[str, str] = {}
        if session.mode == "team":
            info = session.current_round_info()
            team_by_player.update({player: "L" for player in info.get("left_players", [])})
            team_by_player.update({player: "R" for player in info.get("right_players", [])})
        apply_visibility = getattr(self.obs, "apply_match_visibility", None)
        if apply_visibility is None:
            return
        apply_visibility(scene, session.play_type, session.assignments, team_by_player)

    def switch_scoreboard_and_push(self, payloads, warnings: list[str]) -> None:
        switched = self.try_switch_scene(self.state.scenes.get("scoreboard"), warnings)
        if switched:
            self.sleep(SCOREBOARD_SETTLE_SECONDS)
        self.scoreboard.push_all(payloads)

    def save_score_screenshot(self, machine_id: str, png: bytes) -> None:
        with self.lock:
            if self.session is None or self.session.phase not in (
                SessionPhase.LIVE,
                SessionPhase.REVIEW,
            ):
                return
            assigned_machines = {slot["machine"] for slot in self.session.assignments.values()}
            if machine_id not in assigned_machines:
                return
            self.screenshots.save(round_key_for_session(self.session), machine_id, png)

    # ---- 监控 ----

    def start_monitor(self, on_scores, on_update, on_score_frame=None) -> None:
        self.stop_monitor()
        self.monitor = CabinetMonitor(
            obs_host=self.state.obs_host,
            obs_port=self.state.obs_port,
            obs_password=self.obs_password,
            machines=self.state.machines,
            interval=self.state.monitor_interval,
            on_scores=on_scores,
            on_update=on_update,
            on_score_frame=on_score_frame,
        )
        self.monitor.start()

    def stop_monitor(self) -> None:
        if self.monitor is not None:
            self.monitor.stop()
            self.monitor = None

    def monitor_running(self) -> bool:
        return self.monitor is not None and self.monitor.running

    # ---- 广播 ----

    def session_snapshot(self) -> dict[str, Any]:
        self.scenes.update_aliases(self.state.scenes)
        return {
            "session": self.session.snapshot() if self.session else None,
            "obs_connected": self.obs_connected(),
            "monitor_running": self.monitor_running(),
            "mode": self.state.mode,
            "test_mode": self.state.test_mode,
            "scenes": self.state.scenes,
            "actual_scenes": list(self.scenes.snapshots),
            "machines": sorted(self.state.machines),
            "screenshots": self.screenshots.current_urls(self.session),
            "scene": self.current_scene,
            "scene_state": self.scenes.public_state(),
            "pending": self.scenes.pending.to_dict() if self.scenes.pending else None,
        }


def create_app(config_dir: Path | None = None):
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "iidx-director-dev")
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
    ctx = AppContext(config_dir)

    def emit_session() -> None:
        socketio.emit("session_update", ctx.session_snapshot())

    def ok(**extra):
        return jsonify({"success": True, **extra})

    def fail(message: str, **extra):
        return jsonify({"success": False, "error": message, **extra})

    def _overlay_stage(pending) -> bool:
        prior = ctx.scenes.snapshot(pending.scene)
        snapshot = {
            "template": pending.template,
            "texts": pending.texts,
            "hues": pending.hues,
            "version": int(prior.get("version", 0)) + 1,
        }
        if hasattr(ctx.overlay, "stage"):
            return bool(ctx.overlay.stage(pending.scene, snapshot))
        return bool(ctx.overlay.push({
            "cmd": "stage", "scene": pending.scene, "snapshot": snapshot,
        }))

    def _overlay_activate(scene: str) -> bool:
        if hasattr(ctx.overlay, "activate"):
            return bool(ctx.overlay.activate(scene))
        return bool(ctx.overlay.push({"cmd": "activate", "scene": scene}))

    def _execute_pending() -> tuple[bool, str | None, list[str]]:
        """Apply the current pending transaction, retaining it on any failure."""
        warnings: list[str] = []
        pending = ctx.scenes.require_pending()
        stage = pending.failed_stage
        try:
            if pending.status in ("pending", "failed") and pending.failed_stage in (None, "stage"):
                stage = "stage"
                if not _overlay_stage(pending):
                    raise RuntimeError("overlay stage 未确认")
                ctx.scenes.mark("staged")
            if pending.status in ("staged", "failed") and pending.failed_stage in (None, "scene_switch"):
                stage = "scene_switch"
                if not ctx.obs_connected():
                    raise RuntimeError("OBS 未连接")
                if not ctx.try_switch_scene(pending.scene, warnings):
                    raise RuntimeError(f"切换场景 {pending.scene} 失败")
                ctx.scenes.mark("scene_switched")
                ctx.current_scene = pending.scene
            if pending.status in ("scene_switched", "failed") and pending.failed_stage in (None, "activate"):
                stage = "activate"
                if not _overlay_activate(pending.scene):
                    raise RuntimeError("overlay activate 未确认")
                ctx.scenes.mark("scene_switched")

            action = pending.action
            if action == "round_begin" and not pending.action_data.get("done"):
                stage = "action"
                session = _require_session()
                if not pending.action_data.get("visibility_done"):
                    ctx.apply_match_visibility(pending.scene, session)
                    pending.action_data["visibility_done"] = True
                if not pending.action_data.get("session_started"):
                    session.begin_round()
                    pending.action_data["session_started"] = True
                start_payload = pending.action_data.get("start_payload")
                if start_payload and ctx.overlay.push(start_payload) is False:
                    raise RuntimeError("overlay round_start 推送失败")
                pending.action_data["done"] = True
            elif action == "scoreboard" and not pending.action_data.get("scoreboard_done"):
                stage = "action"
                ctx.sleep(SCOREBOARD_SETTLE_SECONDS)
                ctx.scoreboard.push_all(pending.action_data.get("payloads", []))
                pending.action_data["scoreboard_done"] = True
            if action == "scoreboard" and pending.action_data.get("scoreboard_done") and not pending.action_data.get("result_done"):
                stage = "action"
                result_payload = pending.action_data.get("result_payload")
                if result_payload and ctx.overlay.push(result_payload) is False:
                    raise RuntimeError("overlay round_result 推送失败")
                pending.action_data["result_done"] = True
                if result_payload:
                    source_scene = pending.source_scene
                    data = result_payload.get("data", {})
                    if source_scene:
                        prior = ctx.scenes.snapshot(source_scene)
                        ctx.scenes.set_snapshot(
                            source_scene,
                            data.get("template", prior["template"]),
                            data.get("texts", prior["texts"]),
                            data.get("hues", prior["hues"]),
                        )
            ctx.scenes.complete()
            return True, None, warnings
        except Exception as exc:
            ctx.scenes.mark("failed", failed_stage=stage or pending.status, error=str(exc))
            return False, str(exc), warnings

    # ---- 页面 ----

    @app.get("/")
    def page_settings():
        return render_template("settings.html")

    @app.get("/prep")
    def page_prep():
        return render_template("prep.html")

    @app.get("/review")
    def page_review():
        return render_template("review.html")

    @app.get("/overlay/")
    def page_overlay():
        overlay_root = Path(__file__).resolve().parents[1] / "overlay"
        return send_file(overlay_root / "obs-overlay.html", mimetype="text/html")

    @app.get("/overlay/<path:asset_path>")
    def overlay_asset(asset_path: str):
        overlay_root = Path(__file__).resolve().parents[1] / "overlay"
        return send_from_directory(overlay_root, asset_path, max_age=0)

    # Serving the scoreboard pages from the director avoids file:// URLs in
    # OBS Browser Source and keeps all business endpoints on the loopback host.
    @app.get("/scoreboard/bpl/")
    def scoreboard_bpl_index():
        return send_from_directory(MONOREPO_ROOT / "iidx_bpl_scoreboard", "index.html")

    @app.get("/scoreboard/bpl/<path:asset_path>")
    def scoreboard_bpl_asset(asset_path: str):
        return send_from_directory(MONOREPO_ROOT / "iidx_bpl_scoreboard", asset_path, max_age=0)

    @app.get("/scoreboard/knockout/")
    def scoreboard_knockout_index():
        return send_from_directory(MONOREPO_ROOT / "iidx_knockout_scoreboard", "index.html")

    @app.get("/scoreboard/knockout/<path:asset_path>")
    def scoreboard_knockout_asset(asset_path: str):
        return send_from_directory(
            MONOREPO_ROOT / "iidx_knockout_scoreboard", asset_path, max_age=0
        )

    # ---- 状态 ----

    @app.get("/api/state")
    def api_state():
        return ok(**ctx.session_snapshot())

    @app.get("/api/screenshot/<match_id>/<round_key>/<path:machine_id>")
    def api_screenshot(match_id: str, round_key: str, machine_id: str):
        path = ctx.screenshots.resolve(match_id, round_key, machine_id)
        if path is None:
            return fail("截图不存在")
        return send_file(path, mimetype="image/png", max_age=0)

    @socketio.on("connect")
    def on_connect():
        emit_session()

    # ---- OBS ----

    @app.post("/api/obs/connect")
    def api_obs_connect():
        data = request.get_json(force=True)
        try:
            ctx.connect_obs(
                data.get("host", "localhost"),
                int(data.get("port", 4455)),
                data.get("password") or ctx.obs_password,
            )
        except Exception as exc:
            return fail(f"OBS 连接失败: {exc}")
        emit_session()
        return ok()

    @app.post("/api/obs/disconnect")
    def api_obs_disconnect():
        if ctx.obs is not None:
            ctx.obs.disconnect()
            ctx.obs = None
        emit_session()
        return ok()

    @app.get("/api/obs/scenes")
    def api_obs_scenes():
        if not ctx.obs_connected():
            return fail("OBS 未连接")
        try:
            return ok(scenes=ctx.obs.get_scenes())  # type: ignore[union-attr]
        except Exception as exc:
            return fail(str(exc))

    # ---- 比赛设置 ----

    @app.post("/api/mode")
    def api_mode():
        mode = request.get_json(force=True).get("mode")
        if mode not in ("team", "knockout"):
            return fail(f"未知模式: {mode!r}")
        ctx.state.mode = mode
        save_runtime_state(ctx.state)
        emit_session()
        return ok()

    @app.post("/api/test-mode")
    def api_test_mode():
        enabled = request.get_json(force=True).get("enabled")
        if not isinstance(enabled, bool):
            return fail("测试模式开关必须是布尔值")
        with ctx.lock:
            if ctx.session is not None and ctx.session.phase != SessionPhase.IDLE:
                return fail("比赛进行中不能切换测试模式")
            if enabled and ctx.monitor_running():
                # Test mode replaces cabinet capture only; keep the OBS
                # connection available for scene queries and switching.
                ctx.stop_monitor()
            ctx.state.test_mode = enabled
            save_runtime_state(ctx.state)
        emit_session()
        return ok(test_mode=enabled)

    @app.post("/api/config/upload")
    def api_config_upload():
        data = request.get_json(force=True)
        kind = data.get("kind")
        filename = {"team": loader.TEAM_MATCH_FILE, "knockout": loader.KNOCKOUT_FILE}.get(kind)
        if filename is None:
            return fail(f"未知配置类型: {kind!r}")
        try:
            loader.save_config(filename, data.get("content", ""), ctx.config_dir)
        except ConfigError as exc:
            return fail(str(exc))
        return ok()

    @app.get("/api/config/current/<kind>")
    def api_config_current(kind: str):
        try:
            if kind == "team":
                return ok(config=loader.load_team_match(ctx.config_dir).model_dump(by_alias=True))
            if kind == "knockout":
                return ok(config=loader.load_knockout(ctx.config_dir).model_dump(by_alias=True))
        except ConfigError as exc:
            return fail(str(exc))
        return fail(f"未知配置类型: {kind!r}")

    @app.get("/api/config/template/<kind>")
    def api_config_template(kind: str):
        templates = {"team": loader.TEAM_MATCH_TEMPLATE, "knockout": loader.KNOCKOUT_TEMPLATE}
        if kind not in templates:
            return fail(f"未知配置类型: {kind!r}")
        return jsonify(templates[kind])

    # ---- 统一场景 pending 事务 ----

    @app.get("/api/scene/pending")
    def api_scene_pending_get():
        return ok(pending=ctx.scenes.pending.to_dict() if ctx.scenes.pending else None)

    @app.post("/api/scene/pending")
    def api_scene_pending_create():
        data = request.get_json(force=True)
        requested = data.get("scene")
        scene = ctx.scenes.resolve(requested)
        if scene is None:
            return fail("场景未配置")
        template = data.get("template") or template_for_scene(scene, ctx.state.mode)
        try:
            with ctx.lock:
                pending = ctx.scenes.create_pending(
                    scene,
                    template,
                    data.get("texts"),
                    data.get("hues"),
                    source=str(data.get("source") or "shortcut"),
                )
        except PendingError as exc:
            return fail(str(exc))
        emit_session()
        return ok(pending=pending.to_dict())

    @app.post("/api/scene/pending/confirm")
    def api_scene_pending_confirm():
        with ctx.lock:
            try:
                success, error, warnings = _execute_pending()
            except PendingError as exc:
                return fail(str(exc))
        emit_session()
        if not success:
            return fail(error or "场景应用失败", pending=True, warnings=warnings)
        return ok(warnings=warnings)

    @app.post("/api/scene/pending/cancel")
    def api_scene_pending_cancel():
        try:
            with ctx.lock:
                pending = ctx.scenes.cancel(request.get_json(force=True).get("id"))
        except PendingError as exc:
            return fail(str(exc))
        emit_session()
        return ok(cancelled=pending.to_dict())

    # ---- 比赛流程 ----

    @app.post("/api/match/start")
    def api_match_start():
        with ctx.lock:
            if ctx.session is not None and ctx.session.phase != SessionPhase.IDLE:
                return fail("已有进行中的比赛，请先中止")
            try:
                if ctx.state.mode == "team":
                    config = loader.load_team_match(ctx.config_dir)
                    init = ("bpl", bpl_init_payload(config))
                else:
                    config = loader.load_knockout(ctx.config_dir)
                    init = ("knockout", knockout_init_payload(config))
            except ConfigError as exc:
                return fail(str(exc))
            try:
                ctx.scoreboard.push(*init)
            except PushError as exc:
                return fail(f"记分板 init 推送失败: {exc}")
            session = MatchSession(ctx.state.mode, config)
            session.start()
            ctx.session = session
            ctx.current_scene = None
            ctx.screenshots.start_match()
        emit_session()
        return ok()

    @app.post("/api/match/abort")
    def api_match_abort():
        with ctx.lock:
            if ctx.session is None:
                return fail("没有进行中的比赛")
            ctx.session.abort()
            ctx.session = None
            if ctx.scenes.pending is not None:
                ctx.scenes.cancel()
        emit_session()
        return ok()

    @app.post("/api/round/assign")
    def api_round_assign():
        with ctx.lock:
            session = _require_session()
            try:
                session.set_assignments(request.get_json(force=True).get("assignments", {}))
            except SessionError as exc:
                return fail(str(exc))
        emit_session()
        return ok()

    @app.post("/api/round/begin")
    def api_round_begin():
        with ctx.lock:
            session = _require_session()
            if set(session.assignments) != set(session.players_to_assign()):
                return fail("尚未完成机台分配")
            scene = request.get_json(force=True).get("scene") or _default_scene(ctx, session)
            actual_scene = ctx.scenes.resolve(scene)
            if actual_scene is None:
                return fail("场景未配置")
            try:
                ctx.scene_template = template_for_scene(actual_scene, session.mode)
                payload = round_start_payload(session, ctx.scene_template, actual_scene)
                data = payload["data"]
                pending = ctx.scenes.create_pending(
                    actual_scene,
                    ctx.scene_template,
                    data.get("texts", {}),
                    data.get("hues", {}),
                    source="round_start",
                    action="round_begin",
                    action_data={"start_payload": payload},
                )
            except (SessionError, PendingError) as exc:
                return fail(str(exc))
        emit_session()
        return ok(pending=pending.to_dict())

    @app.post("/api/round/confirm")
    def api_round_confirm():
        with ctx.lock:
            session = _require_session()
            if ctx.scenes.pending is not None:
                return fail("已有待应用的场景操作，请先确认、取消或重试")
            scores = {
                k: int(v) for k, v in request.get_json(force=True).get("scores", {}).items()
            }
            try:
                payloads = session.confirm(scores)
            except (SessionError, ValueError) as exc:
                return fail(str(exc))
            scoreboard_scene = ctx.scenes.resolve(ctx.state.scenes.get("scoreboard"))
            if scoreboard_scene is None:
                return fail("计分板场景未配置")
            result_scene = ctx.current_scene or ctx.scenes.resolve(_default_scene(ctx, session)) or "Live"
            result_payload = round_result_payload(session, ctx.scene_template, result_scene)
            try:
                pending = ctx.scenes.create_pending(
                    scoreboard_scene,
                    template_for_scene(scoreboard_scene, session.mode),
                    source="scoreboard",
                    action="scoreboard",
                    action_data={"payloads": payloads, "result_payload": result_payload},
                    source_scene=result_scene,
                )
            except PendingError as exc:
                return fail(str(exc))
        emit_session()
        return ok(pending=pending.to_dict(), repush=True)

    @app.post("/api/round/force_review")
    def api_round_force_review():
        """抓分失败时的应急通道：手动录入本回合 EX 分进入确认环节。"""
        with ctx.lock:
            session = _require_session()
            scores = {
                k: int(v) for k, v in request.get_json(force=True).get("scores", {}).items()
            }
            try:
                session.force_review(scores)
            except (SessionError, ValueError) as exc:
                return fail(str(exc))
        emit_session()
        return ok()

    @app.post("/api/round/repush")
    def api_round_repush():
        with ctx.lock:
            session = _require_session()
            if not session.last_payloads:
                return fail("没有待重推的载荷")
            if ctx.scenes.pending is None:
                scoreboard_scene = ctx.scenes.resolve(ctx.state.scenes.get("scoreboard"))
                if scoreboard_scene is None:
                    return fail("计分板场景未配置")
                try:
                    pending = ctx.scenes.create_pending(
                        scoreboard_scene,
                        template_for_scene(scoreboard_scene, session.mode),
                        source="scoreboard",
                        action="scoreboard",
                        action_data={"payloads": session.last_payloads},
                    )
                except PendingError as exc:
                    return fail(str(exc))
            else:
                pending = ctx.scenes.pending
        emit_session()
        return ok(pending=pending.to_dict())

    @app.post("/api/round/advance")
    def api_round_advance():
        with ctx.lock:
            session = _require_session()
            if ctx.scenes.pending is not None:
                return fail("已有待应用的场景操作，请先确认或取消")
            try:
                session.advance()
            except SessionError as exc:
                return fail(str(exc))
            ended = session.phase == SessionPhase.MATCH_END
            if ended:
                payload = match_end_payload(session, ctx.scene_template, ctx.current_scene or "Live")
                ctx.overlay.push(payload)
                data = payload.get("data", {})
                if ctx.current_scene:
                    prior = ctx.scenes.snapshot(ctx.current_scene)
                    ctx.scenes.set_snapshot(
                        ctx.current_scene,
                        ctx.scene_template or template_for_scene(ctx.current_scene, session.mode),
                        data.get("texts", prior["texts"]),
                        data.get("hues", prior["hues"]),
                    )
        emit_session()
        return ok(match_end=ended)

    @app.post("/api/scoreboard/reset")
    def api_scoreboard_reset():
        board = request.get_json(force=True).get("board")
        payloads = {"bpl": bpl_reset_payload, "knockout": knockout_reset_payload}
        if board not in payloads:
            return fail(f"未知记分板: {board!r}")
        try:
            ctx.scoreboard.push(board, payloads[board]())
        except PushError as exc:
            return fail(str(exc))
        return ok()

    @app.post("/api/obs/switch")
    def api_obs_switch():
        requested = request.get_json(force=True).get("scene")
        if not isinstance(requested, str) or not requested:
            return fail("缺少场景名")
        scene = ctx.scenes.resolve(requested)
        if scene is None:
            return fail("场景未配置")
        try:
            with ctx.lock:
                pending = ctx.scenes.create_pending(
                    scene,
                    template_for_scene(scene, ctx.state.mode),
                    source="shortcut",
                )
        except PendingError as exc:
            return fail(str(exc))
        emit_session()
        return ok(scene=scene, pending=pending.to_dict())

    # ---- 监控 ----

    @app.post("/api/monitor")
    def api_monitor():
        action = request.get_json(force=True).get("action")
        try:
            if action == "start":
                if ctx.state.test_mode:
                    return ok(test_mode=True, message="测试模式无需启动机台监控")
                ctx.start_monitor(_on_scores, _on_update, _on_score_frame)
            elif action == "stop":
                ctx.stop_monitor()
            else:
                return fail(f"未知操作: {action!r}")
        except Exception as exc:
            return fail(f"监控{action}失败: {exc}")
        emit_session()
        return ok()

    @app.post("/api/test/score")
    @app.post("/api/test/scores")
    def api_test_scores():
        """测试模式直接注入某台机台的 1P/2P 成绩，并生成空白截图。"""
        data = request.get_json(force=True)
        machine_id = data.get("machine_id")
        if not isinstance(machine_id, str) or not machine_id:
            return fail("缺少机台编号")
        if not ctx.state.test_mode:
            return fail("测试模式未启用")
        raw_scores = data.get("scores", data)
        if not isinstance(raw_scores, dict):
            return fail("成绩格式无效")
        scores: dict[str, str] = {}
        for side in ("1p", "2p"):
            raw = raw_scores.get(f"{side}score", raw_scores.get(side))
            if raw is None or raw == "":
                continue
            try:
                value = int(raw)
            except (TypeError, ValueError):
                return fail(f"{side.upper()} 分数无效")
            if value < 0:
                return fail(f"{side.upper()} 分数不能为负")
            scores[f"{side}score"] = str(value)
        if not scores:
            return fail("至少填写一个 1P 或 2P 分数")
        with ctx.lock:
            session = _require_session()
            if session.phase != SessionPhase.LIVE:
                return fail(f"当前状态 {session.phase.value} 不能注入测试成绩")
            assigned_machines = {slot["machine"] for slot in session.assignments.values()}
            if machine_id not in assigned_machines:
                return fail("该机台未分配给当前回合")
            ctx.save_score_screenshot(machine_id, EMPTY_SCREENSHOT_PNG)
            transitioned = session.on_machine_scores(machine_id, scores)
        socketio.emit(
            "cabinet_update",
            {"machine_id": machine_id, "label": "测试模式", "state": "RESULT", "scores": scores},
        )
        if transitioned:
            emit_session()
        return ok(machine_id=machine_id, scores=scores, phase=session.phase.value)

    # ---- 监控回调（monitor 线程） ----

    def _on_update(result: dict[str, Any]) -> None:
        socketio.emit(
            "cabinet_update",
            {
                "machine_id": result.get("machine_id"),
                "label": result.get("label"),
                "state": result.get("state"),
            },
        )

    def _on_scores(machine_id: str, scores: dict[str, Any]) -> None:
        with ctx.lock:
            session = ctx.session
            if session is None:
                return
            transitioned = session.on_machine_scores(machine_id, scores)
        socketio.emit(
            "cabinet_update",
            {"machine_id": machine_id, "label": None, "state": None, "scores": scores},
        )
        if transitioned:
            emit_session()

    def _on_score_frame(machine_id: str, png: bytes) -> None:
        ctx.save_score_screenshot(machine_id, png)

    # ---- 工具 ----

    def _require_session() -> MatchSession:
        if ctx.session is None:
            raise SessionError("没有进行中的比赛")
        return ctx.session

    @app.errorhandler(SessionError)
    def handle_session_error(exc):
        return fail(str(exc))

    app.config["CONTEXT"] = ctx
    return app, socketio


def _default_scene(ctx: AppContext, session: MatchSession | None = None) -> str | None:
    """按模式给默认游戏场景；导播可在 PREP 页面改选。"""
    scenes = ctx.state.scenes
    mode = session.mode if session is not None else ctx.state.mode
    play_type = session.play_type if session is not None else "SP"
    play_type = "DP" if play_type == "DP" else "SP"
    if mode == "team":
        round_type = session.current_round_info().get("type") if session else "1v1"
        key = f"team_{play_type.lower()}_{'2v2' if round_type == '2v2' else '1v1'}"
        return (
            scenes.get(key)
            or scenes.get(f"team_{play_type.lower()}")
            or scenes.get("team_sp_1v1")
            or scenes.get("team_sp")
        )
    return (
        scenes.get(f"individual_{play_type.lower()}")
        or scenes.get("individual_sp")
        or scenes.get("individual")
    )


app, socketio = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="IIDX 导播台")
    parser.add_argument(
        "--no-autostart",
        action="store_true",
        help="不自动启动本地识别服务和 WebSocket relay",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    dependencies = None

    def _handle_sigterm(_signum, _frame):
        raise SystemExit(0)

    try:
        if not args.no_autostart:
            dependencies = DependencyManager(Path(__file__).resolve().parents[2])
            dependencies.start()
            signal.signal(signal.SIGTERM, _handle_sigterm)
        host = os.environ.get("IIDX_DIRECTOR_HOST", "127.0.0.1")
        print(f"导播台 @ http://{host}:{WEB_PORT}")
        socketio.run(
            app,
            host=host,
            port=WEB_PORT,
            allow_unsafe_werkzeug=True,
            use_reloader=False,
        )
    finally:
        if dependencies is not None:
            dependencies.stop()


if __name__ == "__main__":
    main()

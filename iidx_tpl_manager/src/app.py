import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_socketio import SocketIO
from pydantic import BaseModel, Field, field_validator

# Support direct execution: python src/app.py
if __package__ in (None, ""):
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.config.loader import ConfigError, get_player_names, load_configs
from src.obs import OBSClient, REQUIRED_SCENES, SceneController
from src.obs.heartbeat import OBSHeartbeat
from src.obs.monitor import CabinetMonitor
from src.scoreboard.pusher import ScoreboardPusher
from src.state import RUNTIME_STATE_PATH, RuntimeState, load_runtime_state, save_runtime_state


class OBSConfigForm(BaseModel):
    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    password: str = ""

    @field_validator("host")
    @classmethod
    def host_must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("host must not be empty")
        return v.strip()


class ModeForm(BaseModel):
    mode: str = Field(..., min_length=1)

    @field_validator("mode")
    @classmethod
    def mode_must_be_valid(cls, v: str) -> str:
        v = v.strip()
        if v not in ("team", "individual"):
            raise ValueError("mode must be 'team' or 'individual'")
        return v


class RoundPrepForm(BaseModel):
    cabinet_1: str = "Unassigned"
    cabinet_2: str = "Unassigned"
    cabinet_3: str = "Unassigned"
    cabinet_4: str = "Unassigned"


class ScoreboardDelayForm(BaseModel):
    delay: float = Field(..., ge=0.0, le=300.0)


def create_app(return_socketio: bool = False):
    project_root = Path(__file__).resolve().parents[1]
    app = Flask(
        __name__,
        template_folder=str(project_root / "src" / "templates"),
        static_folder=str(project_root / "static"),
    )
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

    socketio = SocketIO(app, cors_allowed_origins="*")

    runtime_state = load_runtime_state()
    client = OBSClient(
        host=runtime_state.obs_host,
        port=runtime_state.obs_port,
        password=runtime_state.obs_password,
    )
    scene_controller = SceneController(client)
    app._scene_controller = scene_controller
    app._obs_client = client

    pusher = ScoreboardPusher()
    app._scoreboard_pusher = pusher

    def _validate_and_emit_obs_state() -> None:
        scene_controller.validate_scenes()
        runtime_state = load_runtime_state()
        runtime_state.obs_connected = client.connected
        runtime_state.missing_scenes = scene_controller.missing_scenes
        save_runtime_state(runtime_state)
        socketio.emit(
            "obs_status",
            {
                "connected": client.connected,
                "scenes_valid": scene_controller.scenes_valid,
                "missing_scenes": scene_controller.missing_scenes,
            },
        )

    @app.route("/")
    def status():
        runtime_state = load_runtime_state()
        return render_template(
            "status.html",
            server_port=5002,
            state_path=str(RUNTIME_STATE_PATH),
            config_error=app.config.get("CONFIG_ERROR"),
            runtime_state=runtime_state,
            obs_connected=client.connected,
            scenes_valid=scene_controller.scenes_valid,
            missing_scenes=scene_controller.missing_scenes,
            obs_host=runtime_state.obs_host,
            obs_port=runtime_state.obs_port,
            obs_password=runtime_state.obs_password,
            monitoring_active=runtime_state.monitoring_active,
            scoreboard_delay=runtime_state.scoreboard_delay,
            pending_scores=runtime_state.pending_scores,
        )

    @app.route("/switch_scene", methods=["POST"])
    def switch_scene():
        data = request.get_json(silent=True) or request.form
        scene = (data.get("scene") or "").strip()
        if scene not in REQUIRED_SCENES.values():
            return jsonify({"success": False, "error": "Invalid scene name"}), 200
        ok, error = scene_controller.switch_to(scene)
        if ok:
            return jsonify({"success": True}), 200
        return jsonify({"success": False, "error": error}), 200

    @app.route("/api/scoreboard_delay", methods=["POST"])
    def scoreboard_delay():
        payload = request.get_json(silent=True) or request.form.to_dict()
        try:
            form = ScoreboardDelayForm(**payload)
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 200
        runtime_state = load_runtime_state()
        runtime_state.scoreboard_delay = form.delay
        save_runtime_state(runtime_state)
        socketio.emit("scoreboard_delay_updated", {"delay": form.delay})
        return jsonify({"success": True, "delay": form.delay}), 200

    @app.route("/confirm_score", methods=["POST"])
    def confirm_score():
        runtime_state = load_runtime_state()
        pending = dict(runtime_state.pending_scores)
        if not pending:
            return jsonify({"success": False, "error": "No pending scores"}), 200

        # Validate no invalid scores remain
        for data in pending.values():
            scores = data.get("scores", {})
            if not scores.get("1p_valid", False) or not scores.get("2p_valid", False):
                return jsonify({"success": False, "error": "Invalid scores must be corrected first"}), 200

        # Switch OBS to Scoreboard_web
        ok, error = scene_controller.switch_to("Scoreboard_web")
        if not ok:
            return jsonify({"success": False, "error": error}), 200

        # Build and push score based on mode
        mode = runtime_state.mode
        round_number = runtime_state.current_round
        assignments = runtime_state.cabinet_assignments

        try:
            configs = load_configs()
        except Exception as exc:
            return jsonify({"success": False, "error": f"Failed to load configs: {exc}"}), 200

        if mode == "team":
            # Flatten team schedule to find current match and round
            team_schedule = configs.get("team_schedule")
            if not team_schedule:
                return jsonify({"success": False, "error": "Team schedule not loaded"}), 200

            target_match = None
            target_round_idx = None
            target_round = None
            counter = 0
            for week in team_schedule.weeks:
                for match in week.matches:
                    for idx, r in enumerate(match.rounds):
                        if counter == round_number - 1:
                            target_match = match
                            target_round_idx = idx
                            target_round = r
                            break
                        counter += 1
                    if target_match:
                        break
                if target_match:
                    break

            if target_round is None:
                return jsonify({"success": False, "error": "Round not found in team schedule"}), 200

            round_in_match = target_round_idx + 1

            left_players = set(target_round.left_players)
            right_players = set(target_round.right_players)

            if target_round.type == "1v1":
                # Find the two active players and their scores
                left_score_val = 0
                right_score_val = 0
                left_ex = None
                right_ex = None
                for machine_id, data in pending.items():
                    player = assignments.get(machine_id, "Unassigned")
                    if player == "Unassigned":
                        continue
                    scores = data.get("scores", {})
                    ex_score = scores.get("1p_score") or scores.get("2p_score") or 0
                    if player in left_players:
                        left_ex = ex_score
                    elif player in right_players:
                        right_ex = ex_score
                if left_ex is not None and right_ex is not None:
                    if left_ex >= right_ex:
                        left_score_val = target_round.points
                    else:
                        right_score_val = target_round.points
                pusher.push_team_score(round_in_match, left_score_val, right_score_val)
            else:
                # 2v2: rank all 4 EX scores and assign points
                ex_scores = []
                for machine_id, data in pending.items():
                    player = assignments.get(machine_id, "Unassigned")
                    if player == "Unassigned":
                        continue
                    if player in left_players or player in right_players:
                        scores = data.get("scores", {})
                        ex_score = scores.get("1p_score") or scores.get("2p_score") or 0
                        ex_scores.append({"player": player, "ex": ex_score, "side": "left" if player in left_players else "right"})
                # Sort descending
                ex_scores.sort(key=lambda x: x["ex"], reverse=True)
                # Assign points: 1st=3, 2nd=2, 3rd=1, 4th=0
                rank_points = {0: 3, 1: 2, 2: 1, 3: 0}
                left_score_val = 0
                right_score_val = 0
                for rank, entry in enumerate(ex_scores):
                    pts = rank_points.get(rank, 0)
                    if entry["side"] == "left":
                        left_score_val += pts
                    else:
                        right_score_val += pts
                pusher.push_team_score(round_in_match, left_score_val, right_score_val)
        elif mode == "individual":
            individual_schedule = configs.get("individual_schedule")
            if not individual_schedule:
                return jsonify({"success": False, "error": "Individual schedule not loaded"}), 200

            # Map round to group: flatten groups alphabetically, 4 rounds per group
            groups = sorted(individual_schedule.groups.keys())
            group_idx = (round_number - 1) // 4
            if group_idx >= len(groups):
                return jsonify({"success": False, "error": "Round exceeds available groups"}), 200
            group_name_raw = groups[group_idx]
            group_name = group_name_raw.replace("组", "")
            stage = "quarterfinal"
            if group_name in ("E", "F"):
                stage = "semifinal"
            elif group_name == "finals":
                stage = "final"
            round_in_group = ((round_number - 1) % 4) + 1

            scores = []
            for machine_id in ["IIDX#1", "IIDX#2", "IIDX#3", "IIDX#4"]:
                player = assignments.get(machine_id, "Unassigned")
                if player == "Unassigned":
                    continue
                data = pending.get(machine_id, {})
                score_data = data.get("scores", {})
                ex_score = score_data.get("1p_score") or score_data.get("2p_score") or 0
                scores.append({"player": player, "score": ex_score})
            pusher.push_individual_score(stage, group_name, round_in_group, scores)
        else:
            return jsonify({"success": False, "error": "Unknown tournament mode"}), 200

        # Clear pending scores after push
        runtime_state.pending_scores = {}
        save_runtime_state(runtime_state)
        socketio.emit("scores_pushed", {"mode": mode, "round": round_number})
        return jsonify({"success": True}), 200

    @app.route("/obs_config", methods=["POST"])
    def obs_config():
        payload = request.get_json(silent=True) or request.form.to_dict()
        try:
            form = OBSConfigForm(**payload)
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 200

        runtime_state = load_runtime_state()
        runtime_state.obs_host = form.host
        runtime_state.obs_port = form.port
        runtime_state.obs_password = form.password
        save_runtime_state(runtime_state)

        client.host = form.host
        client.port = form.port
        client.password = form.password
        if client.connected:
            client.disconnect()
        try:
            client.connect()
        except Exception:
            client.connected = False
        _validate_and_emit_obs_state()

        return jsonify(
            {
                "success": True,
                "connected": client.connected,
                "scenes_valid": scene_controller.scenes_valid,
            }
        ), 200

    @app.route("/config")
    def config():
        runtime_state = load_runtime_state()
        player_names = []
        config_error = app.config.get("CONFIG_ERROR")
        if runtime_state.mode and not config_error:
            try:
                loaded = load_configs()
                player_names = get_player_names(loaded, runtime_state.mode)
            except ConfigError:
                pass
        return render_template(
            "config.html",
            config_error=config_error,
            runtime_state=runtime_state,
            player_names=player_names,
        )

    @app.route("/set_mode", methods=["POST"])
    def set_mode():
        payload = request.get_json(silent=True) or request.form.to_dict()
        try:
            form = ModeForm(**payload)
        except Exception as exc:
            if request.is_json:
                return jsonify({"success": False, "error": str(exc)}), 200
            return redirect(url_for("config"))

        runtime_state = load_runtime_state()
        runtime_state.mode = form.mode
        runtime_state.current_round = 1
        runtime_state.cabinet_assignments = {
            f"IIDX#{i}": "Unassigned" for i in range(1, 5)
        }
        save_runtime_state(runtime_state)
        socketio.emit("mode_changed", {"mode": form.mode})
        if request.is_json:
            return jsonify({"success": True, "mode": form.mode}), 200
        return redirect(url_for("config"))

    @app.route("/upload_config", methods=["POST"])
    def upload_config():
        if "config_file" not in request.files:
            if request.is_json:
                return jsonify({"success": False, "error": "No file provided"}), 200
            return redirect(url_for("config"))
        file = request.files["config_file"]
        if file.filename == "":
            if request.is_json:
                return jsonify({"success": False, "error": "No file selected"}), 200
            return redirect(url_for("config"))

        from src.config.loader import CONFIG_FILES

        target_key = None
        for key, (filename, _) in CONFIG_FILES.items():
            if filename == file.filename:
                target_key = key
                break

        if target_key is None:
            valid_names = ", ".join(filename for filename, _ in CONFIG_FILES.values())
            if request.is_json:
                return jsonify(
                    {"success": False, "error": f"Unknown config file. Expected one of: {valid_names}"}
                ), 200
            return redirect(url_for("config"))

        target_filename, model_cls = CONFIG_FILES[target_key]
        target_path = Path("data") / target_filename

        try:
            raw = json.load(file.stream)
            model_cls.model_validate(raw)
        except Exception as exc:
            if request.is_json:
                return jsonify({"success": False, "error": f"Config validation failed: {exc}"}), 200
            return redirect(url_for("config"))

        if target_path.exists():
            backup_path = target_path.with_suffix(f"{target_path.suffix}.bak")
            shutil.copy2(target_path, backup_path)

        file.stream.seek(0)
        with open(target_path, "wb") as f:
            f.write(file.read())

        runtime_state = load_runtime_state()
        runtime_state.current_round = 1
        runtime_state.cabinet_assignments = {
            f"IIDX#{i}": "Unassigned" for i in range(1, 5)
        }
        save_runtime_state(runtime_state)

        try:
            load_configs()
            app.config.pop("CONFIG_ERROR", None)
        except ConfigError as exc:
            app.config["CONFIG_ERROR"] = str(exc)
            if request.is_json:
                return jsonify({"success": False, "error": str(exc)}), 200
            return redirect(url_for("config"))

        socketio.emit("config_uploaded", {"filename": target_filename})
        if request.is_json:
            return jsonify({"success": True, "filename": target_filename}), 200
        return redirect(url_for("config"))

    @app.route("/round_prep")
    def round_prep():
        runtime_state = load_runtime_state()
        player_names = []
        config_error = app.config.get("CONFIG_ERROR")
        if runtime_state.mode and not config_error:
            try:
                loaded = load_configs()
                player_names = get_player_names(loaded, runtime_state.mode)
            except ConfigError:
                pass
        return render_template(
            "round_prep.html",
            config_error=config_error,
            runtime_state=runtime_state,
            player_names=player_names,
        )

    @app.route("/save_round", methods=["POST"])
    def save_round():
        payload = request.get_json(silent=True) or request.form.to_dict()
        try:
            form = RoundPrepForm(**payload)
        except Exception as exc:
            if request.is_json:
                return jsonify({"success": False, "error": str(exc)}), 200
            return redirect(url_for("round_prep"))

        runtime_state = load_runtime_state()
        runtime_state.cabinet_assignments = {
            "IIDX#1": form.cabinet_1,
            "IIDX#2": form.cabinet_2,
            "IIDX#3": form.cabinet_3,
            "IIDX#4": form.cabinet_4,
        }
        save_runtime_state(runtime_state)
        socketio.emit(
            "round_saved",
            {
                "round": runtime_state.current_round,
                "assignments": runtime_state.cabinet_assignments,
            },
        )
        if request.is_json:
            return jsonify({"success": True}), 200
        return redirect(url_for("round_prep"))

    @app.route("/change_round", methods=["POST"])
    def change_round():
        payload = request.get_json(silent=True) or request.form.to_dict()
        direction = (payload.get("direction") or "").strip()
        if direction not in ("prev", "next"):
            if request.is_json:
                return jsonify({"success": False, "error": "Invalid direction"}), 200
            return redirect(url_for("round_prep"))

        runtime_state = load_runtime_state()
        if direction == "prev":
            runtime_state.current_round = max(1, runtime_state.current_round - 1)
        else:
            runtime_state.current_round = runtime_state.current_round + 1
        save_runtime_state(runtime_state)
        socketio.emit("round_changed", {"round": runtime_state.current_round})
        if request.is_json:
            return jsonify({"success": True, "round": runtime_state.current_round}), 200
        return redirect(url_for("round_prep"))

    @socketio.on("obs_reconnect")
    def handle_obs_reconnect():
        if client.connected:
            client.disconnect()
        try:
            client.connect()
        except Exception:
            client.connected = False
        _validate_and_emit_obs_state()

    # Eager config load inside app context
    with app.app_context():
        try:
            loaded = load_configs()
            config_paths = {}
            for key in loaded:
                config_paths[key] = str(Path("data") / f"{key.replace('_schedule', '')}.json")
            # Fix: use proper filenames from loader
            from src.config.loader import CONFIG_FILES

            config_paths = {
                key: str(Path("data") / filename)
                for key, (filename, _) in CONFIG_FILES.items()
            }
            runtime_state = load_runtime_state()
            runtime_state.config_paths = config_paths
            runtime_state.loaded_at = datetime.now(timezone.utc).isoformat()
            save_runtime_state(runtime_state)
        except ConfigError as exc:
            app.config["CONFIG_ERROR"] = str(exc)

        try:
            client.connect()
            _validate_and_emit_obs_state()
        except Exception:
            client.connected = False

    heartbeat = OBSHeartbeat(client, socketio, scene_controller=scene_controller, interval=3.0)
    heartbeat.start()
    # Flask does not provide a standard shutdown hook for the dev server;
    # the heartbeat thread is daemonized and will terminate with the process.

    monitor = CabinetMonitor(socketio, state_machine_config=runtime_state.state_machine_config)
    app._cabinet_monitor = monitor

    # D-07: monitoring does not auto-start on app launch
    runtime_state = load_runtime_state()
    if runtime_state.monitoring_active:
        runtime_state.monitoring_active = False
        save_runtime_state(runtime_state)

    @app.route("/monitor_control", methods=["POST"])
    def monitor_control():
        data = request.get_json(silent=True) or request.form.to_dict()
        action = (data.get("action") or "").strip().lower()
        if action not in ("start", "stop"):
            return jsonify({"success": False, "error": "Invalid action. Use 'start' or 'stop'."}), 200

        runtime_state = load_runtime_state()
        monitor = app._cabinet_monitor

        if action == "start":
            runtime_state.monitoring_active = True
            save_runtime_state(runtime_state)
            monitor.start()
        else:
            runtime_state.monitoring_active = False
            save_runtime_state(runtime_state)
            monitor.stop()

        socketio.emit("monitoring_status", {"active": runtime_state.monitoring_active})
        return jsonify({"success": True, "active": runtime_state.monitoring_active}), 200

    if return_socketio:
        return app, socketio
    return app


if __name__ == "__main__":
    app, socketio = create_app(return_socketio=True)
    socketio.run(app, host="0.0.0.0", port=5002, allow_unsafe_werkzeug=True)

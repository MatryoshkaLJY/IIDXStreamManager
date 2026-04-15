import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO
from pydantic import BaseModel, Field, field_validator

from src.config.loader import ConfigError, load_configs
from src.obs import OBSClient, REQUIRED_SCENES, SceneController
from src.obs.heartbeat import OBSHeartbeat
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


def create_app(return_socketio: bool = False):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

    socketio = SocketIO(app, cors_allowed_origins="*")

    runtime_state = load_runtime_state()
    client = OBSClient(
        host=runtime_state.obs_host,
        port=runtime_state.obs_port,
        password=runtime_state.obs_password,
    )
    scene_controller = SceneController(client)

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

    heartbeat = OBSHeartbeat(client, socketio, interval=3.0)
    heartbeat.start()
    # Flask does not provide a standard shutdown hook for the dev server;
    # the heartbeat thread is daemonized and will terminate with the process.

    if return_socketio:
        return app, socketio
    return app


if __name__ == "__main__":
    app, socketio = create_app(return_socketio=True)
    socketio.run(app, host="0.0.0.0", port=5002, allow_unsafe_werkzeug=True)

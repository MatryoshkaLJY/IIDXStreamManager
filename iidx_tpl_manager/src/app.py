import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, render_template
from flask_socketio import SocketIO

from src.config.loader import ConfigError, load_configs
from src.state import RUNTIME_STATE_PATH, RuntimeState, load_runtime_state, save_runtime_state


def create_app(return_socketio: bool = False):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

    socketio = SocketIO(app, cors_allowed_origins="*")

    @app.route("/")
    def status():
        runtime_state = load_runtime_state()
        return render_template(
            "status.html",
            server_port=5002,
            state_path=str(RUNTIME_STATE_PATH),
            config_error=app.config.get("CONFIG_ERROR"),
            runtime_state=runtime_state,
        )

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
            runtime_state = RuntimeState(
                config_paths=config_paths,
                loaded_at=datetime.now(timezone.utc).isoformat(),
            )
            save_runtime_state(runtime_state)
        except ConfigError as exc:
            app.config["CONFIG_ERROR"] = str(exc)

    if return_socketio:
        return app, socketio
    return app


if __name__ == "__main__":
    app, socketio = create_app(return_socketio=True)
    socketio.run(app, host="0.0.0.0", port=5002, allow_unsafe_werkzeug=True)

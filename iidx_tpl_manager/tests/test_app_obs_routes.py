import json
from unittest.mock import patch

import pytest

from src.app import create_app
from src.obs.client import OBSClient


class TestAppObsRoutes:
    def test_create_app_does_not_crash_when_obs_unavailable(self):
        with patch("src.obs.client.obsws_python.ReqClient") as mock_req:
            mock_req.side_effect = ConnectionRefusedError("Connection refused")
            app = create_app()
            assert app is not None

    def test_switch_scene_returns_error_when_obs_not_ready(self):
        with patch("src.obs.client.obsws_python.ReqClient") as mock_req:
            mock_req.side_effect = ConnectionRefusedError("Connection refused")
            app = create_app()
            client = app.test_client()
            response = client.post(
                "/switch_scene",
                data=json.dumps({"scene": "现场摄像"}),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is False

    def test_switch_scene_succeeds_when_obs_ready(self):
        with patch("src.obs.client.obsws_python.ReqClient") as mock_req:
            mock_instance = mock_req.return_value
            mock_instance.base_client.ws.connected = True
            app = create_app()
            with patch.object(app._scene_controller, "switch_to", return_value=(True, "")):
                test_client = app.test_client()
                response = test_client.post(
                    "/switch_scene",
                    data=json.dumps({"scene": "现场摄像"}),
                    content_type="application/json",
                )
                assert response.status_code == 200
                data = response.get_json()
                assert data["success"] is True

    def test_switch_scene_rejects_unknown_scene(self):
        with patch("src.obs.client.obsws_python.ReqClient") as mock_req:
            mock_req.side_effect = ConnectionRefusedError("Connection refused")
            app = create_app()
            client = app.test_client()
            response = client.post(
                "/switch_scene",
                data=json.dumps({"scene": "InvalidScene"}),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is False

    def test_obs_config_validates_input(self):
        with patch("src.obs.client.obsws_python.ReqClient") as mock_req:
            mock_req.side_effect = ConnectionRefusedError("Connection refused")
            app = create_app()
            client = app.test_client()
            response = client.post(
                "/obs_config",
                data=json.dumps({"host": "", "port": 99999}),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is False

    def test_obs_config_updates_state_and_attempts_connection(self):
        with patch("src.obs.client.obsws_python.ReqClient") as mock_req:
            mock_instance = mock_req.return_value
            mock_instance.base_client.ws.connected = True
            with patch("src.app.save_runtime_state") as mock_save:
                app = create_app()
                client = app.test_client()
                response = client.post(
                    "/obs_config",
                    data=json.dumps({"host": "obs.local", "port": 4444, "password": "secret"}),
                    content_type="application/json",
                )
                assert response.status_code == 200
                data = response.get_json()
                assert data["success"] is True
                mock_save.assert_called()


class TestSocketIOObsReconnect:
    def test_socketio_obs_reconnect_handler_emits_status(self):
        with patch("src.obs.client.obsws_python.ReqClient") as mock_req:
            mock_instance = mock_req.return_value
            mock_instance.base_client.ws.connected = True
            app, socketio = create_app(return_socketio=True)
            test_client = socketio.test_client(app)
            test_client.emit("obs_reconnect")
            received = test_client.get_received()
            events = [r for r in received if r["name"] == "obs_status"]
            assert len(events) >= 1
            assert "connected" in events[0]["args"][0]

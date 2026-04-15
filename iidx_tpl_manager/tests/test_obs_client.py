from unittest.mock import MagicMock, patch

import pytest

from src.obs.client import OBSClient


class TestOBSClient:
    def test_client_stores_params_without_connecting(self):
        client = OBSClient(host="obs.local", port=4444, password="secret")
        assert client.host == "obs.local"
        assert client.port == 4444
        assert client.password == "secret"
        assert client._client is None

    def test_connected_is_false_before_connect(self):
        client = OBSClient()
        assert client.connected is False

    def test_connect_instantiates_reqclient(self):
        with patch("src.obs.client.obsws_python.ReqClient") as mock_req:
            client = OBSClient(host="obs.local", port=4444, password="secret")
            client.connect()
            mock_req.assert_called_once_with(
                host="obs.local",
                port=4444,
                password="secret",
                timeout=3,
            )

    def test_disconnect_clears_client(self):
        client = OBSClient()
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_base = MagicMock()
        mock_base.ws = mock_ws
        client._client = MagicMock()
        client._client.base_client = mock_base
        client._client.disconnect = MagicMock()

        assert client.connected is True
        client.disconnect()
        assert client._client is None
        assert client.connected is False

    def test_get_version_calls_client(self):
        client = OBSClient()
        client._client = MagicMock()
        client._client.get_version.return_value = {"version": "30.0"}
        result = client.get_version()
        client._client.get_version.assert_called_once()
        assert result == {"version": "30.0"}

    def test_get_scene_list_calls_send_with_getscenelist(self):
        client = OBSClient()
        client._client = MagicMock()
        client._client.send.return_value = {"scenes": []}
        result = client.get_scene_list(raw=True)
        client._client.send.assert_called_once_with("GetSceneList", raw=True)
        assert result == {"scenes": []}

    def test_set_current_program_scene_delegates_to_client(self):
        client = OBSClient()
        client._client = MagicMock()
        client.set_current_program_scene("现场摄像")
        client._client.set_current_program_scene.assert_called_once_with("现场摄像")

    def test_get_version_raises_when_not_connected(self):
        client = OBSClient()
        with pytest.raises(RuntimeError, match="not connected"):
            client.get_version()

    def test_get_scene_list_raises_when_not_connected(self):
        client = OBSClient()
        with pytest.raises(RuntimeError, match="not connected"):
            client.get_scene_list()

    def test_set_current_program_scene_raises_when_not_connected(self):
        client = OBSClient()
        with pytest.raises(RuntimeError, match="not connected"):
            client.set_current_program_scene("现场摄像")

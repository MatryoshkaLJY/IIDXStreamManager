import time
from unittest.mock import MagicMock, Mock

import pytest

from src.obs.heartbeat import OBSHeartbeat


class TestOBSHeartbeat:
    def test_heartbeat_starts_and_stops_without_crash(self):
        obs = Mock()
        socketio = Mock()
        hb = OBSHeartbeat(obs, socketio, interval=0.1)
        hb.start()
        assert hb._thread is not None
        assert hb._thread.is_alive()
        hb.stop()
        assert not hb._thread.is_alive()

    def test_heartbeat_emits_status_on_each_tick(self):
        obs = Mock()
        obs.connected = True
        socketio = Mock()
        hb = OBSHeartbeat(obs, socketio, interval=0.1)
        hb.start()
        time.sleep(0.25)
        hb.stop()
        assert socketio.emit.call_count >= 1
        for call in socketio.emit.call_args_list:
            assert call[0][0] == "obs_status"
            assert "connected" in call[0][1]

    def test_heartbeat_sets_connected_false_on_exception(self):
        obs = Mock()
        obs.connected = True
        obs.get_version.side_effect = RuntimeError("boom")
        socketio = Mock()
        hb = OBSHeartbeat(obs, socketio, interval=0.1)
        hb.start()
        time.sleep(0.25)
        hb.stop()
        assert obs.connected is False
        emit_calls = [c for c in socketio.emit.call_args_list if c[0][0] == "obs_status"]
        assert any(c[0][1]["connected"] is False for c in emit_calls)

    def test_heartbeat_does_not_auto_reconnect(self):
        obs = Mock()
        obs.connected = False
        socketio = Mock()
        hb = OBSHeartbeat(obs, socketio, interval=0.1)
        hb.start()
        time.sleep(0.25)
        hb.stop()
        obs.connect.assert_not_called()

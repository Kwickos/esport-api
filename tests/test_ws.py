"""WebSocket live endpoint smoke test."""

from fastapi.testclient import TestClient

from app.main import app


def test_live_ws_sends_subscribed_ack():
    with TestClient(app) as client, client.websocket_connect("/live/game-1") as ws:
        assert ws.receive_json() == {"type": "subscribed", "game_id": "game-1"}
        ws.close()  # clean client close -> handler detects disconnect and returns

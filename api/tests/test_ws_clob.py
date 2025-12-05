"Tests for ws_clob.py"

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
from api.ws_clob import PolymarketWS, app, asset_connections, asset_queues
from fastapi import WebSocket
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_globals():
    """Clear global dictionaries before each test."""
    asset_queues.clear()
    asset_connections.clear()
    yield
    asset_queues.clear()
    asset_connections.clear()


@pytest.mark.asyncio
async def test_subscribe_unsubscribe_and_disconnect(monkeypatch):
    """Test subscribing, unsubscribing, and disconnect behavior."""

    # Mock PolymarketWS to avoid real WebSocket connections
    mock_start = MagicMock()
    monkeypatch.setattr("api.ws_clob.PolymarketWS.start", mock_start)

    with client.websocket_connect("/ws/clob") as websocket:
        # Subscribe to two assets
        websocket.send_text(
            json.dumps({"action": "subscribe", "asset_ids": ["asset1", "asset2"]})
        )
        response = websocket.receive_json()
        assert response["status"] == "subscribed"
        assert set(response["asset_ids"]) == {"asset1", "asset2"}

        # Check that asset_queues has two entries
        assert "asset1" in asset_queues
        assert "asset2" in asset_queues
        # There should be one queue per asset (the client)
        for asset in ["asset1", "asset2"]:
            assert len(asset_queues[asset]) == 1
            queue = next(iter(asset_queues[asset]))
            assert isinstance(queue, asyncio.Queue)

        # Mock a message from PolymarketWS
        test_message = json.dumps({"token_id": "asset1", "price": 42})
        # Call on_message directly
        pol_ws = PolymarketWS(["asset1"])
        pol_ws.on_message(test_message)

        # The client queue should get the message
        queue = next(iter(asset_queues["asset1"]))
        received = await queue.get()
        assert received["price"] == 42
        assert received["token_id"] == "asset1"

        # Disconnect client
        websocket.send_text(json.dumps({"action": "disconnect"}))
        # WebSocket closes automatically
        websocket.close()
        # Queues should be cleared for this client
        assert asset_queues["asset1"] == set()
        assert asset_queues["asset2"] == set()


@pytest.mark.asyncio
async def test_invalid_action_returns_error():
    """Test sending invalid action."""
    with client.websocket_connect("/ws/clob") as websocket:
        websocket.send_text(json.dumps({"action": "invalid_action"}))
        response = websocket.receive_json()
        assert "error" in response
        assert "Invalid action" in response["error"]


@pytest.mark.asyncio
async def test_multiple_clients_sharing_asset(monkeypatch):
    """Test that two clients subscribing to the same asset don't interfere."""

    mock_start = MagicMock()
    monkeypatch.setattr("api.ws_clob.PolymarketWS.start", mock_start)

    # Client 1
    with client.websocket_connect("/ws/clob") as ws1:
        ws1.send_text(
            json.dumps({"action": "subscribe", "asset_ids": ["asset_shared"]})
        )
        ws1.receive_json()
        assert "asset_shared" in asset_queues
        queue1 = next(iter(asset_queues["asset_shared"]))

        # Client 2
        with client.websocket_connect("/ws/clob") as ws2:
            ws2.send_text(
                json.dumps({"action": "subscribe", "asset_ids": ["asset_shared"]})
            )
            ws2.receive_json()
            queue2 = None
            for q in asset_queues["asset_shared"]:
                if q != queue1:
                    queue2 = q
            assert queue2 is not None

            # Check both queues exist
            assert len(asset_queues["asset_shared"]) == 2

            # Send a message from PolymarketWS
            test_message = json.dumps({"token_id": "asset_shared", "price": 99})
            pol_ws = PolymarketWS(["asset_shared"])
            pol_ws.on_message(test_message)

            # Both clients' queues should get the message
            msg1 = await queue1.get()
            msg2 = await queue2.get()
            assert msg1["price"] == 99
            assert msg2["price"] == 99

            # Client 1 disconnects
            ws1.send_text(json.dumps({"action": "disconnect"}))
            ws1.close()
            # The asset queue should still contain client 2
            assert queue2 in asset_queues["asset_shared"]
            assert queue1 not in asset_queues["asset_shared"]

            # Client 2 disconnects
            ws2.send_text(json.dumps({"action": "disconnect"}))
            ws2.close()
            # No queues left
            assert asset_queues["asset_shared"] == set()

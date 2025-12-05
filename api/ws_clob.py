"API to subscribe to and unsubscribe from realtime data stream for an asset"

import asyncio
import json
import threading
import time
from typing import Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websocket import WebSocketApp

app = FastAPI(title="Polymarket CLOB WebSocket Broadcast")

# Globals for managing subscriptions
asset_queues: Dict[str, Set[asyncio.Queue]] = {}  # asset_id -> set of client queues
asset_connections: Dict[str, "PolymarketWS"] = {}  # asset_id -> PolymarketWS object


class PolymarketWS:
    """Single connection per asset, broadcasts to all client queues."""

    def __init__(self, asset_ids: List[str]):
        self.asset_ids = asset_ids
        self.ws = WebSocketApp(
            "wss://ws-subscriptions-clob.polymarket.com/ws/market",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
        )
        self.thread = threading.Thread(target=self.ws.run_forever, daemon=True)

    def start(self):
        "Start thread"
        self.thread.start()

    def on_open(self, ws):
        "Method on opening websocket"
        ws.send(json.dumps({"assets_ids": self.asset_ids, "type": "market"}))
        threading.Thread(target=self.ping, args=(ws,), daemon=True).start()

    def ping(self, ws):
        "Pping method for testing"
        while True:
            ws.send("PING")
            time.sleep(10)

    def on_message(self, message):
        "asset price retrieval"
        try:
            data = json.loads(message)
            asset_id = data.get("token_id") or data.get("asset_id")
            if asset_id and asset_id in asset_queues:
                for queue in asset_queues[asset_id]:
                    asyncio.run_coroutine_threadsafe(
                        queue.put(data), asyncio.get_event_loop()
                    )
        except Exception as e:
            print("Error broadcasting message:", e)

    def on_error(self, error):
        "Error handling"
        print("Polymarket WS Error:", error)

    def on_close(self):
        "Closing method"
        print("Polymarket WS closed")


@app.websocket("/ws/clob")
async def clob_ws(websocket: WebSocket):
    """main websocket logic"""

    await websocket.accept()
    queue = asyncio.Queue()
    subscribed_assets: Set[str] = set()

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            action = data.get("action")
            assets = data.get("asset_ids", [])
            if action == "disconnect":
                # Remove client from all subscribed assets
                for asset_id in subscribed_assets:
                    asset_queues[asset_id].discard(queue)
                subscribed_assets.clear()
                await websocket.close()
                break

            if action == "subscribe":
                for asset_id in assets:
                    if asset_id not in asset_queues:
                        asset_queues[asset_id] = set()
                    asset_queues[asset_id].add(queue)
                    subscribed_assets.add(asset_id)
                    if asset_id not in asset_connections:
                        conn = PolymarketWS([asset_id])
                        conn.start()
                        asset_connections[asset_id] = conn
                await websocket.send_json({"status": "subscribed", "asset_ids": assets})

            elif action == "disconnect":
                # Remove client from all subscribed assets
                for asset_id in subscribed_assets:
                    asset_queues[asset_id].discard(queue)
                subscribed_assets.clear()
                await websocket.close()
                break

            else:
                await websocket.send_json(
                    {"error": "Invalid action. Use subscribe/unsubscribe/disconnect."}
                )

            # Forward any pending messages from the queue
            while not queue.empty():
                message = await queue.get()
                await websocket.send_json(message)

    except WebSocketDisconnect:
        # Remove client from subscribed assets
        for asset_id in subscribed_assets:
            asset_queues[asset_id].discard(queue)
        print("Client disconnected")

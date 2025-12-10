"Historical price retrieval with caching and real time web socket data stream"

import asyncio
import json
import threading
import time
from typing import Dict, List, Set

import httpx
from aiocache import Cache, cached
from aiocache.serializers import JsonSerializer
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from websocket import WebSocketApp

app = FastAPI(title="Polymarket historical price, clob price, and websocket price")

HISTORICAL_PRICE_URL = "https://clob.polymarket.com/prices-history"

WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
asset_queues: Dict[str, Set[asyncio.Queue]] = {}
asset_connections: Dict[str, "PolymarketWS"] = {}

# Default Redis cache settings
DEFAULT_CACHE_SETTINGS = {
    "cache": Cache.REDIS,
    "endpoint": "redis",
    "port": 6379,
    "namespace": "historical",
    "serializer": JsonSerializer(),
    "ttl": 3600,  # 1 hour
}


def historical_key_builder(func, *args, **kwargs):
    """Key builder function for caching"""
    return f"history:{kwargs['asset_id']}:{kwargs.get('interval', 'max')}"


# Fetch single asset from API with caching
@cached(**DEFAULT_CACHE_SETTINGS, key_builder=historical_key_builder)
async def fetch_historical(asset_id: str, interval: str = "max") -> Dict:
    """Method to get historical price of an asset from polymarket"""
    params = {"market": asset_id, "interval": interval}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(HISTORICAL_PRICE_URL, params=params)
        resp.raise_for_status()
        return resp.json()


# GET endpoint
@app.get("/historical_prices")
async def get_historical_prices(
    assets: List[str] = Query(..., description="Comma-separated list of asset IDs"),
    interval: str = Query("max", description="Interval for historical data"),
):
    """
    Example request: /historical_prices?assets=token_id_1,token_id_2&interval=1d
    """
    if not assets:
        return {}

    # Fetch cached data per asset
    tasks = [fetch_historical(asset_id=a, interval=interval) for a in assets]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    result = {}
    for asset, data in zip(assets, responses):
        if isinstance(data, Exception):
            print(f"Error fetching {asset}: {data}")
            continue
        result[asset] = data

    return result


class PolymarketWS:
    """Websocket Class for polymarket websocket endpoint"""

    def __init__(self, asset_ids: List[str]):
        self.asset_ids = asset_ids
        self.ws = WebSocketApp(
            WS_URL,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
        )
        self.thread = threading.Thread(target=self.ws.run_forever, daemon=True)

    def start(self):
        """Create starting thread"""
        self.thread.start()

    def on_open(self, ws):
        """Opening method"""
        payload = {"assets_ids": self.asset_ids, "type": "market"}
        ws.send(json.dumps(payload))
        threading.Thread(target=self.ping, args=(ws,), daemon=True).start()

    def ping(self, ws):
        """Ping helper for checking"""
        while True:
            try:
                ws.send("PING")
                time.sleep(10)
            except Exception:
                break

    def on_message(self, message):
        """Method to check if current queue has asset stream in it"""
        try:
            data = json.loads(message)
            asset_id = data.get("token_id") or data.get("asset_id")
            if asset_id and asset_id in asset_queues:
                for queue in asset_queues[asset_id]:
                    asyncio.run_coroutine_threadsafe(
                        queue.put(data), asyncio.get_event_loop()
                    )
        except Exception:
            pass

    def on_error(self, error):
        """General error method"""
        print(f"WS Error: {error}")

    def on_close(self, *_):
        """Closing method"""
        print("WS Closed")


@app.websocket("/real_time_ws_price")
async def clob_ws(websocket: WebSocket):
    """Method to subscribe or unsubscribe from data stream for a set of assets"""
    await websocket.accept()
    queue = asyncio.Queue()
    subscribed_assets: Set[str] = set()

    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            action = data.get("action")
            assets = data.get("asset_ids", [])

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
                break

            while not queue.empty():
                await websocket.send_json(await queue.get())

    except WebSocketDisconnect:
        pass
    finally:
        for asset_id in subscribed_assets:
            if asset_id in asset_queues:
                asset_queues[asset_id].discard(queue)

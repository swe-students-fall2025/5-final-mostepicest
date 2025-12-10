"Historical price retrieval with caching and real time web socket data stream"

import asyncio
import os
from typing import Dict, List

import httpx
from aiocache import Cache, cached
from aiocache.serializers import JsonSerializer
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

app = FastAPI(title="Polymarket historical price, clob price, and websocket price")

HISTORICAL_PRICE_URL = "https://clob.polymarket.com/prices-history"


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
async def fetch_historical(
    asset_id: str, interval: str = "1h", fidelity: int = 0
) -> Dict:
    """Method to get historical price of an asset from polymarket"""
    params = {"market": asset_id, "interval": interval, "fidelity": fidelity}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(HISTORICAL_PRICE_URL, params=params)
        resp.raise_for_status()
        return resp.json()


# GET endpoint
@app.get("/historical_prices")
async def get_historical_prices(
    assets: List[str] = Query(..., description="Comma-separated list of asset IDs"),
    interval: str = Query("1h", description="Interval for historical data"),
    fidelity: int = Query(None, description="Minimum fidelity (number of data points)"),
):
    """
    Example request: /historical_prices?assets=token_id_1,token_id_2&interval=1d&fidelity=10
    """
    if not assets:
        return {}
    # Fetch cached data per asset
    tasks = [
        fetch_historical(asset_id=a, interval=interval, fidelity=fidelity)
        for a in assets
    ]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    result = {}
    for asset, data in zip(assets, responses):
        if isinstance(data, Exception):
            print(f"Error fetching {asset}: {data}")
            continue

        # Apply fidelity filtering if specified
        if fidelity is not None and isinstance(data, dict) and "history" in data:
            history = data["history"]
            if isinstance(history, list) and len(history) > fidelity:
                # Sample every Nth point to get approximately 'fidelity' points
                step = max(1, len(history) // fidelity)
                filtered_history = [history[i] for i in range(0, len(history), step)]
                # Always include the last point
                if len(filtered_history) == 0 or filtered_history[-1] != history[-1]:
                    filtered_history.append(history[-1])
                data["history"] = filtered_history

        result[asset] = data

    return result


Cache.DEFAULT_SETTINGS = {
    "cache": Cache.REDIS,
    "endpoint": os.getenv("REDIS_HOST", "redis"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "ttl": 5,  # short TTL for near-realtime prices
    "serializer": JsonSerializer(),
    "namespace": "clob_price",
}

client = ClobClient("https://clob.polymarket.com")


class RetryableHTTPError(Exception):
    """Raised when a CLOB request should be retried."""

    pass


@retry(
    retry=retry_if_exception_type(RetryableHTTPError),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(5),
)
async def fetch_clob_prices(tokens: List[str]):
    """Fetch real-time prices from CLOB with retry/backoff"""
    try:
        book_params = [BookParams(token_id=t, side="BUY") for t in tokens]
        prices = client.get_prices(book_params)
    except Exception as e:
        raise RetryableHTTPError(f"Failed to fetch CLOB prices: {e}") from e

    result = []
    for _, p in prices.items():
        result.append(p["BUY"])
    return result


@cached(
    key_builder=lambda f, *args, **kwargs: "clob:" + "_".join(str(t) for t in args[0])
)
async def get_clob_prices(tokens: List[str]):
    """Cached wrapper around fetch_clob_prices."""
    return await fetch_clob_prices(tokens)


@app.get("/clob")
async def clob_endpoint(
    tokens: str = Query(..., description="Comma-separated list of CLOB token IDs")
):
    """
    Get CLOB prices for a set of token IDs.
    Returns a list of dicts including `best_bid`, `best_ask`, and calculated `mid_price`.
    """

    token_list = [t.strip() for t in tokens.split(",") if t.strip()]
    if not token_list:
        raise HTTPException(status_code=400, detail="No valid tokens provided")
    result = await get_clob_prices(token_list)
    print("IN CLOB ", result)
    return JSONResponse(result)

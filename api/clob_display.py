import os
from typing import List

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

# Initialize FastAPI
app = FastAPI(title="Polymarket CLOB Realtime API")

# Redis cache configuration (optional)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

Cache.DEFAULT_SETTINGS = {
    "cache": "aiocache.RedisCache",
    "endpoint": REDIS_HOST,
    "port": REDIS_PORT,
    "ttl": 5,  # 5-second TTL for near real-time
    "serializer": JsonSerializer(),
    "namespace": "clob",
}

# Read-only CLOB client
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
    """
    Fetch real-time prices from CLOB with retry/backoff.
    """
    try:
        book_params = [BookParams(token_id=t) for t in tokens]
        prices = client.get_prices(book_params)
    except Exception as e:
        raise RetryableHTTPError(f"Failed to fetch CLOB prices: {e}")

    # Convert to JSON-serializable dicts
    return [p.to_dict() for p in prices]


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
    """ """
    token_list = [t.strip() for t in tokens.split(",") if t.strip()]
    if not token_list:
        raise HTTPException(status_code=400, detail="No valid tokens provided")

    result = await get_clob_prices(token_list)
    return JSONResponse(result)

"API to search polymarket"

import logging
import asyncio
import os
import sys
from typing import Dict, Set

import httpx
from aiocache import Cache, cached
from aiocache.serializers import JsonSerializer
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

SEARCH_URL = "https://gamma-api.polymarket.com/public-search"

# Redis Config
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

logging.basicConfig(
    level=logging.INFO,  # INFO and above
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout  # ensure it goes to stdout for Docker
)

app = FastAPI(title="Polymarket Search")

# --- REDIS CACHE SETUP ---
try:
    Cache.DEFAULT_SETTINGS = {
        "cache": "aiocache.RedisCache",
        "endpoint": REDIS_HOST,
        "port": REDIS_PORT,
        "ttl": 60,
        "serializer": JsonSerializer(),
        "namespace": "search",
    }
except Exception:
    print("Redis not configured, caching disabled.")

asset_queues: Dict[str, Set[asyncio.Queue]] = {}
asset_connections: Dict[str, "PolymarketWS"] = {}


@cached(key_builder=lambda f, *args, **kwargs: f"page:{args[0]}:{args[0]}")
async def get_polymarket_search(q: str, page: int):
    """Method to search polymarket"""
    params = {"q": q, 
              "cache": "true", 
              "search_profiles": "false",
              "search_tags":"false",
              "page": page}
    print(params)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(SEARCH_URL, params=params)
    return resp.json()


@app.get("/search")
async def search(q: str = Query(..., min_length=1), page: int = 1):
    """Helper to search markets"""
    try:
        data = await get_polymarket_search(q, page)
        return JSONResponse(data)
    except Exception as e:
        logging.error("Search error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not retrieve query detail={e}") from e

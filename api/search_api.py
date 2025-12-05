"""Search api for polymarket"""

import os
import httpx
from aiocache import Cache, cached
from aiocache.serializers import JsonSerializer
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

SEARCH_URL = "https://gamma-api.polymarket.com/public-search"
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

app = FastAPI(title="Polymarket Search API")

# Configure Redis cache
Cache.DEFAULT_SETTINGS = {
    "cache": "aiocache.RedisCache",
    "endpoint": REDIS_HOST,
    "port": REDIS_PORT,
    "ttl": 60,
    "serializer": JsonSerializer(),
    "namespace": "main",
}


@cached(key_builder=lambda f, *args, **kwargs: f"page:{kwargs['q']}:{kwargs['page']}")
async def get_polymarket_search(q: str, page: int):
    """Fetch a single page from Polymarket with caching."""
    params = {"q": q, "cache": "true", "page": page}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(SEARCH_URL, params=params)
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Network error: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}") from e

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@app.get("/search")
async def search_markets(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number (defaults to 1)"),
):
    """Single-page search with Redis caching."""
    result = await get_polymarket_search(q=q, page=page)
    return JSONResponse(result)

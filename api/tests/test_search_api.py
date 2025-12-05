"""Tests for search_api.py"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
from api.search_api import app
from fastapi import HTTPException
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.mark.asyncio
async def test_get_polymarket_search_success():
    """Test that get_polymarket_search returns JSON on success."""
    # Import here to ensure fresh import
    from api import search_api

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"events": [{"id": 1, "name": "Test Market"}]}

    # Create a proper async context manager mock
    async def mock_async_client(*args, **kwargs):
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        return mock_client

    # Patch AsyncClient to return our mock in a context manager
    with patch.object(search_api.httpx, "AsyncClient") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=mock_response))
        )
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_instance

        # Call the function bypassing cache
        result = await search_api.get_polymarket_search.__wrapped__(q="russia", page=1)

    assert result == {"events": [{"id": 1, "name": "Test Market"}]}


@pytest.mark.asyncio
async def test_get_polymarket_search_http_error():
    """Test that HTTP errors raise HTTPException."""
    from api import search_api

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch.object(search_api.httpx, "AsyncClient") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=mock_response))
        )
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_instance

        with pytest.raises(HTTPException) as excinfo:
            await search_api.get_polymarket_search.__wrapped__(q="russia", page=1)

    assert excinfo.value.status_code == 500
    assert "Internal Server Error" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_polymarket_search_network_error():
    """Test network errors raise HTTPException."""
    from api import search_api

    with patch.object(search_api.httpx, "AsyncClient") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(
            return_value=MagicMock(
                get=AsyncMock(side_effect=httpx.RequestError("Connection failed"))
            )
        )
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_instance

        with pytest.raises(HTTPException) as excinfo:
            await search_api.get_polymarket_search.__wrapped__(q="russia", page=1)

    assert excinfo.value.status_code == 500
    assert "Network error" in excinfo.value.detail


def test_search_markets_endpoint(monkeypatch):
    """Test the /search endpoint returns correct JSON."""
    mock_result = {"events": [{"id": 1, "name": "Test Market"}]}

    async def mock_cached(q, page):
        return mock_result

    # Patch get_polymarket_search to use the mock
    monkeypatch.setattr("api.search_api.get_polymarket_search", mock_cached)

    response = client.get("/search?q=russia&page=1")
    assert response.status_code == 200
    assert response.json() == mock_result


def test_search_markets_endpoint_default_page(monkeypatch):
    """Test /search endpoint with no page number defaults to 1."""
    mock_result = {"events": [{"id": 1, "name": "Test Market"}]}

    async def mock_cached(q, page):
        assert page == 1
        return mock_result

    monkeypatch.setattr("api.search_api.get_polymarket_search", mock_cached)

    response = client.get("/search?q=russia")
    assert response.status_code == 200
    assert response.json() == mock_result


def test_search_markets_endpoint_invalid_page(monkeypatch):
    """Test FastAPI validation rejects negative page numbers."""
    response = client.get("/search?q=russia&page=-1")
    assert response.status_code == 422  # Unprocessable Entity due to validation

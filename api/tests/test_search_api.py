"""Tests for search_api.py"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
from api.search_api import app
from fastapi import HTTPException
from fastapi.testclient import TestClient

client = TestClient(app)


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

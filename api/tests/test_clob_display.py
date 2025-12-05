"Tests for clob_display.py"

from unittest.mock import MagicMock

import pytest
from api.clob_display import app, get_clob_prices
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.mark.asyncio
async def test_fetch_clob_prices_and_cache(monkeypatch):
    """Test fetching CLOB prices and caching."""

    # Mock result
    mock_prices = [
        {"token_id": "t1", "price": 42},
        {"token_id": "t2", "price": 100},
    ]

    # Mock fetch_clob_prices to return our mock result
    async def mock_fetch(tokens):
        return mock_prices

    # Patch fetch_clob_prices, NOT get_clob_prices
    monkeypatch.setattr("api.clob_display.fetch_clob_prices", mock_fetch)

    # Call the cached wrapper
    result1 = await get_clob_prices(["t1", "t2"])
    assert result1 == mock_prices

    # Call again to test caching (should return same result)
    result2 = await get_clob_prices(["t1", "t2"])
    assert result2 == mock_prices


def test_clob_endpoint_success(monkeypatch):
    """Test the /clob endpoint returns expected data."""
    mock_result = [{"token_id": "t1", "price": 42}, {"token_id": "t2", "price": 100}]

    async def mock_get(tokens):
        return mock_result

    # Patch get_clob_prices to return mock result
    monkeypatch.setattr("api.clob_display.get_clob_prices", mock_get)

    response = client.get("/clob?tokens=t1,t2")
    assert response.status_code == 200
    assert response.json() == mock_result


def test_clob_endpoint_invalid_tokens(monkeypatch):
    """Test /clob returns 400 if no valid tokens provided."""
    response = client.get("/clob?tokens=   , , ")
    assert response.status_code == 400
    assert response.json()["detail"] == "No valid tokens provided"


def test_clob_endpoint_single_token(monkeypatch):
    """Test /clob with a single token."""
    mock_result = [{"token_id": "t1", "price": 42}]

    async def mock_get(tokens):
        return mock_result

    monkeypatch.setattr("api.clob_display.get_clob_prices", mock_get)

    response = client.get("/clob?tokens=t1")
    assert response.status_code == 200
    assert response.json() == mock_result


@pytest.mark.asyncio
async def test_fetch_clob_prices_retry(monkeypatch):
    """Test that fetch_clob_prices retries on RetryableHTTPError."""

    from api.clob_display import RetryableHTTPError, fetch_clob_prices

    call_count = 0

    def side_effect(book_params):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return [MagicMock(to_dict=lambda: {"token_id": "t1", "price": 42})]

    # Patch client.get_prices to raise exception initially
    monkeypatch.setattr("api.clob_display.client.get_prices", side_effect)

    result = await fetch_clob_prices(["t1"])
    assert result == [{"token_id": "t1", "price": 42}]
    assert call_count == 3

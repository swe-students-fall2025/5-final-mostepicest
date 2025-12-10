"Tests for price_api CLOB endpoint"

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.price_api import RetryableHTTPError, app, fetch_clob_prices, get_clob_prices

client = TestClient(app)


@pytest.mark.asyncio
async def test_get_clob_prices_cached(monkeypatch):
    """get_clob_prices should return cached data when fetch is patched."""
    mock_prices = [{"token_id": "t1", "price": 42}, {"token_id": "t2", "price": 100}]

    async def mock_fetch(tokens):
        return mock_prices

    monkeypatch.setattr("api.price_api.fetch_clob_prices", mock_fetch)

    result1 = await get_clob_prices(["t1", "t2"])
    result2 = await get_clob_prices(["t1", "t2"])
    assert result1 == mock_prices
    assert result2 == mock_prices


def test_clob_endpoint_success(monkeypatch):
    """Test /clob returns mocked data when get_clob_prices is patched."""
    mock_result = [{"token_id": "t1", "price": 42}, {"token_id": "t2", "price": 100}]

    async def mock_get(tokens):
        return mock_result

    monkeypatch.setattr("api.price_api.get_clob_prices", mock_get)

    response = client.get("/clob?tokens=t1,t2")
    assert response.status_code == 200
    assert response.json() == mock_result


def test_clob_endpoint_invalid_tokens():
    """Test /clob returns 400 if no valid tokens provided."""
    response = client.get("/clob?tokens=   , , ")
    assert response.status_code == 400
    assert response.json()["detail"] == "No valid tokens provided"


def test_clob_endpoint_single_token(monkeypatch):
    """Test /clob with a single token."""
    mock_result = [{"token_id": "t1", "price": 42}]

    async def mock_get(tokens):
        return mock_result

    monkeypatch.setattr("api.price_api.get_clob_prices", mock_get)

    response = client.get("/clob?tokens=t1")
    assert response.status_code == 200
    assert response.json() == mock_result


@pytest.mark.asyncio
async def test_fetch_clob_prices_retry(monkeypatch):
    """Test that fetch_clob_prices retries and returns parsed data."""

    call_count = 0

    def fake_prices(book_params):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return {"t1": {"BUY": {"token_id": "t1", "price": 42}}}

    monkeypatch.setattr("api.price_api.client.get_prices", fake_prices)

    result = await fetch_clob_prices(["t1"])
    assert result == [{"token_id": "t1", "price": 42}]
    assert call_count == 3

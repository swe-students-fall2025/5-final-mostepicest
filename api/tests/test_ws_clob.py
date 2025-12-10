"Tests for websocket pricing are deprecated; ensure clob endpoint works."

import pytest
from fastapi.testclient import TestClient

from api.price_api import app

client = TestClient(app)


def test_clob_endpoint_exists():
    response = client.get("/clob?tokens=t1")
    assert response.status_code in (200, 400)


"""Tests for US-30 defense-sector API."""

from fastapi.testclient import TestClient

from app.api.stocks import SUPPORTED_STOCKS
from app.main import app

client = TestClient(app)


def test_get_defense_sector_success():
    """The defense-sector endpoint returns HTTP 200."""
    response = client.get("/sector/defense")

    assert response.status_code == 200


def test_get_defense_sector_data():
    """The endpoint returns the supported companies."""
    response = client.get("/sector/defense")
    data = response.json()

    assert data["sector"] == "defense"
    assert data["count"] == len(SUPPORTED_STOCKS)

    returned_stocks = {
        stock["ticker"]: stock["company_name"]
        for stock in data["stocks"]
    }

    assert returned_stocks == SUPPORTED_STOCKS


def test_get_defense_sector_response_structure():
    """Each stock has the required response fields."""
    response = client.get("/sector/defense")
    data = response.json()

    assert isinstance(data["stocks"], list)
    assert data["count"] == len(data["stocks"])

    for stock in data["stocks"]:
        assert "ticker" in stock
        assert "company_name" in stock
        assert isinstance(stock["ticker"], str)
        assert isinstance(stock["company_name"], str)

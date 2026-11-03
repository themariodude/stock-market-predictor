"""Tests for US-30 defense-sector API."""

from fastapi.testclient import TestClient

from app.api.stocks import SUPPORTED_STOCKS
from app.main import app
from app.services.historical_stock_data import HistoricalStockDataError

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
        stock["ticker"]: stock["company_name"] for stock in data["stocks"]
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


def test_defense_performance_calculation(monkeypatch):
    """Verify equal-weighted cumulative sector returns."""
    ending_prices = {
        "LMT": 110,
        "RTX": 120,
        "NOC": 90,
        "GD": 100,
        "LHX": 105,
        "BA": 95,
    }

    def mock_history(ticker, time_range):
        assert time_range == "1Y"
        return {
            "ticker": ticker,
            "data": [
                {"date": "2026-01-02", "close": 100},
                {
                    "date": "2026-01-05",
                    "close": ending_prices[ticker],
                },
            ],
        }

    monkeypatch.setattr(
        "app.api.sector.get_historical_stock_data",
        mock_history,
    )

    response = client.get("/sector/defense/performance")

    assert response.status_code == 200
    data = response.json()

    assert data["sector"] == "defense"
    assert data["time_range"] == "1Y"
    assert data["count"] == 2

    assert data["data"][0]["cumulative_return_pct"] == 0
    assert data["data"][1]["cumulative_return_pct"] == 3.3333
    assert data["data"][1]["stock_returns_pct"]["LMT"] == 10
    assert data["data"][1]["stock_returns_pct"]["NOC"] == -10


def test_defense_performance_invalid_range():
    """Invalid time ranges return HTTP 400."""
    response = client.get("/sector/defense/performance?time_range=INVALID")

    assert response.status_code == 400


def test_defense_performance_data_failure(monkeypatch):
    """Upstream historical data failures return HTTP 502."""

    def mock_failure(ticker, time_range):
        raise HistoricalStockDataError("Data unavailable")

    monkeypatch.setattr(
        "app.api.sector.get_historical_stock_data",
        mock_failure,
    )

    response = client.get("/sector/defense/performance")

    assert response.status_code == 502


def test_defense_performance_insufficient_data(monkeypatch):
    """Insufficient history returns HTTP 502."""

    def mock_history(ticker, time_range):
        return {
            "ticker": ticker,
            "data": [
                {"date": "2026-01-02", "close": 100},
            ],
        }

    monkeypatch.setattr(
        "app.api.sector.get_historical_stock_data",
        mock_history,
    )

    response = client.get("/sector/defense/performance")

    assert response.status_code == 502

"""Tests for US-30 benchmark comparison API."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.historical_stock_data import HistoricalStockDataError

client = TestClient(app)


def test_benchmark_calculation(monkeypatch):
    """Verify stock and benchmark cumulative returns."""

    def mock_history(ticker, time_range):
        assert time_range == "1Y"

        prices = {
            "LMT": [100, 110],
            "SPY": [200, 210],
        }

        return {
            "ticker": ticker,
            "data": [
                {"date": "2026-01-02", "close": prices[ticker][0]},
                {"date": "2026-01-05", "close": prices[ticker][1]},
            ],
        }

    monkeypatch.setattr(
        "app.api.benchmark.get_historical_stock_data",
        mock_history,
    )

    response = client.get("/benchmark/LMT")

    assert response.status_code == 200
    data = response.json()

    assert data["ticker"] == "LMT"
    assert data["benchmark"] == "SPY"
    assert data["count"] == 2

    final = data["data"][1]
    assert final["stock_return_pct"] == 10
    assert final["benchmark_return_pct"] == 5
    assert final["excess_return_pct"] == 5


def test_benchmark_invalid_ticker():
    """Unsupported stocks return HTTP 404."""
    response = client.get("/benchmark/INVALID")

    assert response.status_code == 404


def test_benchmark_invalid_range():
    """Invalid time ranges return HTTP 400."""
    response = client.get("/benchmark/LMT?time_range=INVALID")

    assert response.status_code == 400


def test_benchmark_invalid_benchmark():
    """Unsupported benchmarks return HTTP 400."""
    response = client.get("/benchmark/LMT?benchmark=INVALID")

    assert response.status_code == 400


def test_benchmark_data_failure(monkeypatch):
    """Historical data failures return HTTP 502."""

    def mock_failure(ticker, time_range):
        raise HistoricalStockDataError("Data unavailable")

    monkeypatch.setattr(
        "app.api.benchmark.get_historical_stock_data",
        mock_failure,
    )

    response = client.get("/benchmark/LMT")

    assert response.status_code == 502


def test_benchmark_insufficient_data(monkeypatch):
    """Insufficient common dates return HTTP 502."""

    def mock_history(ticker, time_range):
        return {
            "ticker": ticker,
            "data": [
                {"date": "2026-01-02", "close": 100},
            ],
        }

    monkeypatch.setattr(
        "app.api.benchmark.get_historical_stock_data",
        mock_history,
    )

    response = client.get("/benchmark/LMT")

    assert response.status_code == 502

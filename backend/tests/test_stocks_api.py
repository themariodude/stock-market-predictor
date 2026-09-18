from fastapi.testclient import TestClient

from app.main import app
from app.services.current_stock_info import StockDataError
from app.services.historical_stock_data import HistoricalStockDataError

client = TestClient(app)


def test_list_supported_stocks():
    response = client.get("/stocks")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 6

    tickers = {stock["ticker"] for stock in data}

    assert tickers == {
        "LMT",
        "RTX",
        "NOC",
        "GD",
        "LHX",
        "BA",
    }


def test_unsupported_stock_returns_404():
    response = client.get("/stocks/AAPL")

    assert response.status_code == 404
    assert response.json() == {"detail": "Unsupported stock ticker: AAPL"}


def test_stock_details_success_and_normalizes_ticker(monkeypatch):
    def fake_current_stock_info(ticker):
        assert ticker == "LMT"

        return {
            "ticker": "LMT",
            "current_price": 485.50,
            "previous_close": 480.00,
            "price_change": 5.50,
            "percent_change": 1.15,
            "volume": 1234567,
        }

    monkeypatch.setattr(
        "app.api.stocks.get_current_stock_info",
        fake_current_stock_info,
    )

    response = client.get("/stocks/lmt")

    assert response.status_code == 200

    data = response.json()

    assert data["ticker"] == "LMT"
    assert data["company_name"] == "Lockheed Martin"
    assert data["current_price"] == 485.50


def test_stock_history_success_and_default_range(monkeypatch):
    fake_result = {
        "ticker": "LMT",
        "time_range": "1Y",
        "period": "1y",
        "count": 1,
        "data": [
            {
                "date": "2026-09-15",
                "open": 475.00,
                "high": 486.00,
                "low": 474.00,
                "close": 485.50,
                "volume": 1234567,
            }
        ],
    }

    def fake_historical_stock_data(ticker, time_range):
        assert ticker == "LMT"
        assert time_range == "1Y"
        return fake_result

    monkeypatch.setattr(
        "app.api.stocks.get_historical_stock_data",
        fake_historical_stock_data,
    )

    response = client.get("/stocks/LMT/history")

    assert response.status_code == 200
    assert response.json() == fake_result


def test_invalid_history_range_returns_400(monkeypatch):
    def fake_historical_stock_data(ticker, time_range):
        raise ValueError("Unsupported time range")

    monkeypatch.setattr(
        "app.api.stocks.get_historical_stock_data",
        fake_historical_stock_data,
    )

    response = client.get("/stocks/LMT/history?time_range=INVALID")

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported time range"}


def test_service_failure_returns_502(monkeypatch):
    def fake_current_stock_info(ticker):
        raise StockDataError("Market data unavailable")

    monkeypatch.setattr(
        "app.api.stocks.get_current_stock_info",
        fake_current_stock_info,
    )

    response = client.get("/stocks/LMT")

    assert response.status_code == 502
    assert response.json() == {"detail": "Market data unavailable"}


def test_history_service_failure_returns_502(monkeypatch):
    def fake_historical_stock_data(ticker, time_range):
        raise HistoricalStockDataError("Historical data unavailable")

    monkeypatch.setattr(
        "app.api.stocks.get_historical_stock_data",
        fake_historical_stock_data,
    )

    response = client.get("/stocks/LMT/history")

    assert response.status_code == 502

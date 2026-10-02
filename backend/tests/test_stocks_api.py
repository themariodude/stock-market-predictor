from fastapi.testclient import TestClient

from app.main import app
from app.services.current_stock_info import StockDataError
from app.services.historical_stock_data import HistoricalStockDataError
from app.services.prediction_direction import PredictionDirectionError
from app.services.stock_prediction import StockPredictionError

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


def test_stock_prediction_direction_success(monkeypatch):
    fake_result = {
        "ticker": "LMT",
        "prediction_direction": "UP",
        "direction_label": "Upward",
        "current_price": 485.50,
        "predicted_price": 489.25,
        "predicted_change": 3.75,
        "predicted_percent_change": 0.77,
        "prediction_confidence": 72.5,
        "prediction_uncertainty": 27.5,
        "confidence_label": "High confidence",
    }

    def fake_prediction_direction(ticker):
        assert ticker == "LMT"
        return fake_result

    monkeypatch.setattr(
        "app.api.stocks.get_prediction_direction",
        fake_prediction_direction,
    )

    response = client.get("/stocks/lmt/prediction-direction")

    assert response.status_code == 200
    assert response.json() == {
        "company_name": "Lockheed Martin",
        **fake_result,
    }


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


def test_prediction_direction_service_failure_returns_502(monkeypatch):
    def fake_prediction_direction(ticker):
        raise PredictionDirectionError("Prediction unavailable")

    monkeypatch.setattr(
        "app.api.stocks.get_prediction_direction",
        fake_prediction_direction,
    )

    response = client.get("/stocks/LMT/prediction-direction")

    assert response.status_code == 502
    assert response.json() == {"detail": "Prediction unavailable"}

def test_stock_prediction_success(monkeypatch):
    fake_result = {
        "ticker": "LMT",
        "model": "LinearRegression",
        "training_count": 200,
        "test_count": 50,
        "dates": [
            "2026-09-29",
            "2026-09-30",
        ],
        "actual": [
            482.50,
            485.25,
        ],
        "predictions": [
            481.75,
            484.90,
        ],
    }

    def fake_stock_prediction(ticker):
        assert ticker == "LMT"
        return fake_result

    monkeypatch.setattr(
        "app.api.stocks.get_stock_prediction",
        fake_stock_prediction,
    )

    response = client.get("/stocks/lmt/prediction")

    assert response.status_code == 200
    assert response.json() == {
        "company_name": "Lockheed Martin",
        **fake_result,
    }


def test_stock_prediction_service_failure_returns_502(monkeypatch):
    def fake_stock_prediction(ticker):
        raise StockPredictionError("Prediction unavailable")

    monkeypatch.setattr(
        "app.api.stocks.get_stock_prediction",
        fake_stock_prediction,
    )

    response = client.get("/stocks/LMT/prediction")

    assert response.status_code == 502
    assert response.json() == {"detail": "Prediction unavailable"}
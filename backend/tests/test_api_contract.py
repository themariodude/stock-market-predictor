"""Regression tests for the public stock, prediction, and health API contract."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.prediction_direction import PredictionDirectionError

client = TestClient(app)


def assert_keys(value, expected):
    assert isinstance(value, dict)
    assert set(value) == set(expected)


def assert_number(value):
    assert type(value) in (int, float)


def assert_number_or_none(value):
    assert value is None or type(value) in (int, float)


def test_health_response_contract(monkeypatch):
    monkeypatch.setattr("app.main._engine", None)

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert_keys(data, {"status", "database"})
    assert type(data["status"]) is str
    assert type(data["database"]) is str
    assert data == {"status": "ok", "database": "unconfigured"}


def test_supported_stocks_response_contract():
    response = client.get("/stocks")

    assert response.status_code == 200
    data = response.json()
    assert type(data) is list
    assert len(data) == 6
    for stock in data:
        assert_keys(stock, {"ticker", "company_name"})
        assert type(stock["ticker"]) is str
        assert type(stock["company_name"]) is str


def test_stock_details_response_contract(monkeypatch):
    monkeypatch.setattr(
        "app.api.stocks.get_current_stock_info",
        lambda ticker: {
            "ticker": ticker,
            "current_price": 485.5,
            "previous_close": 480.0,
            "price_change": 5.5,
            "percent_change": 1.15,
            "volume": 1234567,
        },
    )

    response = client.get("/stocks/lmt")

    assert response.status_code == 200
    data = response.json()
    assert_keys(
        data,
        {
            "company_name",
            "ticker",
            "current_price",
            "previous_close",
            "price_change",
            "percent_change",
            "volume",
        },
    )
    assert type(data["company_name"]) is str
    assert type(data["ticker"]) is str
    for field in ("current_price", "previous_close", "price_change", "percent_change"):
        assert_number_or_none(data[field])
    assert type(data["volume"]) is int or data["volume"] is None


def test_stock_history_response_contract(monkeypatch):
    monkeypatch.setattr(
        "app.api.stocks.get_historical_stock_data",
        lambda ticker, time_range: {
            "ticker": ticker,
            "time_range": time_range,
            "period": "1y",
            "count": 1,
            "data": [
                {
                    "date": "2026-09-15",
                    "open": 475.0,
                    "high": 486.0,
                    "low": 474.0,
                    "close": 485.5,
                    "volume": 1234567,
                }
            ],
        },
    )

    response = client.get("/stocks/LMT/history")

    assert response.status_code == 200
    data = response.json()
    assert_keys(data, {"ticker", "time_range", "period", "count", "data"})
    for field in ("ticker", "time_range", "period"):
        assert type(data[field]) is str
    assert type(data["count"]) is int
    assert type(data["data"]) is list
    assert len(data["data"]) == data["count"]
    for record in data["data"]:
        assert_keys(record, {"date", "open", "high", "low", "close", "volume"})
        assert type(record["date"]) is str
        for field in ("open", "high", "low", "close"):
            assert_number(record[field])
        assert type(record["volume"]) is int


def test_prediction_direction_response_contract(monkeypatch):
    monkeypatch.setattr(
        "app.api.stocks.get_prediction_direction",
        lambda ticker: {
            "ticker": ticker,
            "as_of_date": "2026-09-15",
            "prediction_direction": "UP",
            "direction_label": "Upward",
            "current_price": 100.0,
            "predicted_price": 101.0,
            "predicted_change": 1.0,
            "predicted_percent_change": 1.0,
            "prediction_confidence": None,
            "prediction_uncertainty": None,
            "confidence_label": "Unavailable",
            "explanation": {
                "method": "momentum",
                "summary": "Uses the recent average daily price change.",
                "horizon": "next_trading_day",
                "window": {
                    "range": "1M",
                    "start_date": "2026-09-01",
                    "end_date": "2026-09-15",
                    "start_close": 99.0,
                    "end_close": 100.0,
                    "closing_prices": 2,
                },
                "factors": [
                    {
                        "name": "recent_trend",
                        "label": "Average daily change (1M)",
                        "value": 1.0,
                        "unit": "USD/day",
                        "role": "Sets the direction and predicted price",
                        "influence": None,
                    },
                    {
                        "name": "daily_volatility",
                        "label": "Typical daily swing (1M)",
                        "value": None,
                        "unit": "USD",
                        "role": "Larger swings lower the confidence score",
                        "influence": None,
                    },
                ],
                "confidence_basis": "Relative trend strength and daily swings.",
                "not_used": ["Trading volume"],
                "limitations": ["News and market events are not considered."],
            },
        },
    )
    monkeypatch.setattr(
        "app.api.stocks.get_economic_factors",
        lambda as_of_date: [
            {
                "id": "unemployment_rate",
                "name": "Unemployment rate",
                "value": 4.1,
                "unit": "%",
                "published_on": "2026-09-10",
                "age_days": 5,
            }
        ],
    )

    response = client.get("/stocks/LMT/prediction-direction")

    assert response.status_code == 200
    data = response.json()
    assert_keys(
        data,
        {
            "company_name",
            "ticker",
            "as_of_date",
            "prediction_direction",
            "direction_label",
            "current_price",
            "predicted_price",
            "predicted_change",
            "predicted_percent_change",
            "prediction_confidence",
            "prediction_uncertainty",
            "confidence_label",
            "explanation",
            "economic_factors",
        },
    )
    for field in (
        "company_name",
        "ticker",
        "as_of_date",
        "prediction_direction",
        "direction_label",
        "confidence_label",
    ):
        assert type(data[field]) is str
    for field in (
        "current_price",
        "predicted_price",
        "predicted_change",
        "predicted_percent_change",
        "prediction_confidence",
        "prediction_uncertainty",
    ):
        assert_number_or_none(data[field])

    explanation = data["explanation"]
    assert_keys(
        explanation,
        {
            "method",
            "summary",
            "horizon",
            "window",
            "factors",
            "confidence_basis",
            "not_used",
            "limitations",
        },
    )
    for field in ("method", "summary", "horizon", "confidence_basis"):
        assert type(explanation[field]) is str
    window = explanation["window"]
    assert_keys(
        window,
        {
            "range",
            "start_date",
            "end_date",
            "start_close",
            "end_close",
            "closing_prices",
        },
    )
    for field in ("range", "start_date", "end_date"):
        assert type(window[field]) is str
    for field in ("start_close", "end_close"):
        assert_number(window[field])
    assert type(window["closing_prices"]) is int
    assert type(explanation["factors"]) is list
    for factor in explanation["factors"]:
        assert_keys(factor, {"name", "label", "value", "unit", "role", "influence"})
        for field in ("name", "label", "unit", "role"):
            assert type(factor[field]) is str
        assert_number_or_none(factor["value"])
        assert factor["influence"] is None
    for field in ("not_used", "limitations"):
        assert type(explanation[field]) is list
        assert all(type(item) is str for item in explanation[field])
    assert type(data["economic_factors"]) is list
    for factor in data["economic_factors"]:
        assert_keys(
            factor,
            {"id", "name", "value", "unit", "published_on", "age_days"},
        )
        for field in ("id", "name", "unit", "published_on"):
            assert type(factor[field]) is str
        assert_number(factor["value"])
        assert type(factor["age_days"]) is int


def test_ml_prediction_response_contract(monkeypatch):
    monkeypatch.setattr(
        "app.api.stocks.get_stock_prediction",
        lambda ticker: {
            "ticker": ticker,
            "model": "LinearRegression",
            "training_count": 200,
            "test_count": 2,
            "dates": ["2026-09-14", "2026-09-15"],
            "actual": [482.5, 485.25],
            "predictions": [481.75, 484.9],
        },
    )

    response = client.get("/stocks/LMT/prediction")

    assert response.status_code == 200
    data = response.json()
    assert_keys(
        data,
        {
            "company_name",
            "ticker",
            "model",
            "training_count",
            "test_count",
            "dates",
            "actual",
            "predictions",
        },
    )
    for field in ("company_name", "ticker", "model"):
        assert type(data[field]) is str
    for field in ("training_count", "test_count"):
        assert type(data[field]) is int
    for field in ("dates", "actual", "predictions"):
        assert type(data[field]) is list
    assert all(type(value) is str for value in data["dates"])
    assert all(type(value) in (int, float) for value in data["actual"])
    assert all(type(value) in (int, float) for value in data["predictions"])
    assert len(data["dates"]) == len(data["actual"]) == len(data["predictions"])
    assert data["test_count"] == len(data["predictions"])


def test_model_metrics_response_contract(monkeypatch):
    monkeypatch.setattr(
        "app.api.models.load_model_metrics",
        lambda: {
            "baseline": {"mae": 2.0, "rmse": 3.0},
            "model": {"mae": 1.5, "rmse": 2.5},
        },
    )

    response = client.get("/models/metrics")

    assert response.status_code == 200
    data = response.json()
    assert_keys(data, {"baseline", "model"})
    for section in data.values():
        assert_keys(section, {"mae", "rmse"})
        assert_number(section["mae"])
        assert_number(section["rmse"])


def test_unsupported_tickers_return_contract_error_for_critical_routes():
    paths = (
        "/stocks/AAPL",
        "/stocks/AAPL/history",
        "/stocks/AAPL/prediction-direction",
        "/stocks/AAPL/prediction",
    )

    for path in paths:
        response = client.get(path)
        assert response.status_code == 404
        assert_keys(response.json(), {"detail"})
        assert response.json() == {"detail": "Unsupported ticker: AAPL"}


def test_invalid_history_range_returns_contract_error():
    response = client.get("/stocks/LMT/history?time_range=INVALID")

    assert response.status_code == 400
    assert_keys(response.json(), {"detail"})
    assert response.json() == {
        "detail": (
            "Unsupported time range 'INVALID'. Supported ranges are: "
            "1M, 3M, 6M, 1Y, 5Y, MAX."
        )
    }


def test_prediction_service_failure_returns_contract_error(monkeypatch):
    def fail_prediction(ticker):
        raise PredictionDirectionError("Prediction unavailable")

    monkeypatch.setattr("app.api.stocks.get_prediction_direction", fail_prediction)

    response = client.get("/stocks/LMT/prediction-direction")

    assert response.status_code == 502
    assert response.json() == {"detail": "Prediction unavailable"}

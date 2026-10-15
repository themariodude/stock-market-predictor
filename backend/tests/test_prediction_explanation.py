"""US-17 - Understand Prediction Factors."""

from statistics import pstdev

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.prediction_direction import get_prediction_direction

HISTORY_PATH = "app.services.prediction_direction.get_historical_stock_data"


def fake_history(closes, volume=1_000_000):
    """Build historical records in the shape get_historical_stock_data returns."""
    return {
        "data": [
            {"date": f"2026-09-{day:02d}", "close": close, "volume": volume}
            for day, close in enumerate(closes, start=1)
        ]
    }


def patch_history(monkeypatch, history):
    monkeypatch.setattr(HISTORY_PATH, lambda symbol, time_range: history)


def factors_by_name(result):
    return {factor["name"]: factor for factor in result["explanation"]["factors"]}


def test_explanation_describes_momentum_method(monkeypatch):
    patch_history(monkeypatch, fake_history([100.0, 102.0, 101.0, 104.0, 103.0]))

    explanation = get_prediction_direction("LMT")["explanation"]

    assert explanation["method"] == "momentum"
    assert explanation["horizon"] == "next_trading_day"
    assert explanation["summary"]
    assert explanation["confidence_basis"]
    assert explanation["limitations"]


def test_recent_trend_matches_predicted_change(monkeypatch):
    patch_history(monkeypatch, fake_history([100.0, 102.0, 101.0, 104.0, 103.0]))

    result = get_prediction_direction("LMT")
    trend = factors_by_name(result)["recent_trend"]

    assert trend["value"] == pytest.approx(result["predicted_change"], abs=0.011)
    assert trend["unit"] == "USD/day"


def test_daily_volatility_reproduces_confidence(monkeypatch):
    closes = [100.0, 102.0, 101.0, 104.0, 103.0]
    patch_history(monkeypatch, fake_history(closes))

    result = get_prediction_direction("LMT")
    volatility = factors_by_name(result)["daily_volatility"]

    changes = [later - earlier for earlier, later in zip(closes, closes[1:])]
    expected_volatility = pstdev(changes)
    trend_strength = abs(sum(changes) / len(changes))
    expected_confidence = round(
        trend_strength / (trend_strength + expected_volatility) * 100, 1
    )

    assert volatility["value"] == round(expected_volatility, 2)
    assert result["prediction_confidence"] == expected_confidence


def test_window_matches_priced_records_and_skips_missing_closes(monkeypatch):
    history = fake_history([100.0, 102.0, 101.0, 104.0])
    history["data"][0]["close"] = None
    patch_history(monkeypatch, history)

    result = get_prediction_direction("LMT")
    window = result["explanation"]["window"]
    factors = factors_by_name(result)

    # Valid closes 102, 101, 104 -> changes -1, +3 -> mean +1, population std 2
    assert result["predicted_change"] == pytest.approx(1.0)
    assert result["predicted_price"] == pytest.approx(105.0)
    assert factors["recent_trend"]["value"] == pytest.approx(1.0)
    assert factors["daily_volatility"]["value"] == pytest.approx(2.0)
    assert window["start_date"] == "2026-09-02"
    assert window["end_date"] == "2026-09-04"
    assert window["start_close"] == 102.0
    assert window["end_close"] == 104.0
    assert window["closing_prices"] == 3


def test_window_range_matches_requested_history(monkeypatch):
    requested_ranges = []

    def fake_get_history(symbol, time_range):
        requested_ranges.append(time_range)
        return fake_history([100.0, 101.0, 103.0])

    monkeypatch.setattr(HISTORY_PATH, fake_get_history)

    window = get_prediction_direction("LMT")["explanation"]["window"]

    assert requested_ranges == ["1M"]
    assert window["range"] == "1M"


def test_factors_exclude_volume_and_economic_indicators(monkeypatch):
    patch_history(monkeypatch, fake_history([100.0, 102.0, 101.0], volume=9_999_999))

    explanation = get_prediction_direction("LMT")["explanation"]
    names = {factor["name"] for factor in explanation["factors"]}

    assert names == {"recent_trend", "daily_volatility"}
    assert "Trading volume" in explanation["not_used"]
    assert any("Economic indicators" in item for item in explanation["not_used"])


def test_two_closes_give_explanation_without_volatility(monkeypatch):
    patch_history(monkeypatch, fake_history([100.0, 101.5]))

    result = get_prediction_direction("LMT")
    factors = factors_by_name(result)

    assert result["prediction_confidence"] is None
    assert factors["daily_volatility"]["value"] is None
    assert factors["recent_trend"]["value"] == 1.5


def test_influence_is_null_for_momentum_method(monkeypatch):
    patch_history(monkeypatch, fake_history([100.0, 102.0, 101.0, 104.0]))

    factors = get_prediction_direction("LMT")["explanation"]["factors"]

    assert all(factor["influence"] is None for factor in factors)


def test_downtrend_uses_independently_calculated_momentum(monkeypatch):
    patch_history(monkeypatch, fake_history([110.0, 106.0, 107.0, 101.0]))

    result = get_prediction_direction("LMT")
    trend = factors_by_name(result)["recent_trend"]

    # Changes -4, +1, -6 -> mean -3
    assert trend["value"] == pytest.approx(-3.0)
    assert result["predicted_change"] == pytest.approx(-3.0)
    assert result["predicted_price"] == pytest.approx(98.0)
    assert result["prediction_direction"] == "DOWN"


def test_flat_prices_give_zero_factors_and_full_confidence(monkeypatch):
    patch_history(monkeypatch, fake_history([100.0, 100.0, 100.0]))

    result = get_prediction_direction("LMT")
    factors = factors_by_name(result)

    assert result["prediction_direction"] == "FLAT"
    assert result["prediction_confidence"] == 100.0
    assert factors["recent_trend"]["value"] == 0.0
    assert factors["daily_volatility"]["value"] == 0.0


def test_volume_does_not_change_forecast_or_explanation(monkeypatch):
    closes = [100.0, 102.0, 101.0, 104.0]

    patch_history(monkeypatch, fake_history(closes, volume=1))
    low_volume = get_prediction_direction("LMT")

    patch_history(monkeypatch, fake_history(closes, volume=999_999_999))
    high_volume = get_prediction_direction("LMT")

    assert low_volume == high_volume


def test_api_returns_explanation_alongside_existing_fields(monkeypatch):
    patch_history(monkeypatch, fake_history([100.0, 102.0, 101.0, 104.0, 103.0]))
    monkeypatch.setattr("app.api.stocks.get_economic_factors", lambda as_of_date: [])

    response = TestClient(app).get("/stocks/LMT/prediction-direction")

    assert response.status_code == 200
    data = response.json()
    assert data["prediction_direction"] == "UP"
    assert data["predicted_price"] == pytest.approx(103.75)
    assert data["economic_factors"] == []
    assert data["explanation"]["method"] == "momentum"
    assert data["explanation"]["window"]["end_date"] == data["as_of_date"]

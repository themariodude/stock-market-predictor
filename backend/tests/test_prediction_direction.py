import pytest

from app.services.prediction_direction import (
    PredictionDirectionError,
    calculate_prediction_confidence,
    classify_prediction_confidence,
    classify_prediction_direction,
    get_prediction_direction,
)


def test_empty_ticker_raises_value_error():
    with pytest.raises(ValueError):
        get_prediction_direction("")


@pytest.mark.parametrize(
    ("current_price", "predicted_price", "expected_direction"),
    [
        (100.00, 101.00, "UP"),
        (100.00, 99.00, "DOWN"),
        (100.00, 100.00, "FLAT"),
    ],
)
def test_classify_prediction_direction(
    current_price,
    predicted_price,
    expected_direction,
):
    assert (
        classify_prediction_direction(current_price, predicted_price)
        == expected_direction
    )


@pytest.mark.parametrize(
    ("confidence_score", "expected_label"),
    [
        (85.0, "High confidence"),
        (55.0, "Medium confidence"),
        (25.0, "Low confidence"),
    ],
)
def test_classify_prediction_confidence(confidence_score, expected_label):
    assert classify_prediction_confidence(confidence_score) == expected_label


def test_calculate_prediction_confidence_requires_multiple_changes():
    result = calculate_prediction_confidence([2.0])

    assert result == {
        "prediction_confidence": None,
        "prediction_uncertainty": None,
        "confidence_label": "Unavailable",
    }


def test_prediction_direction_uses_average_recent_change(monkeypatch):
    def fake_historical_stock_data(ticker, time_range):
        assert ticker == "LMT"
        assert time_range == "1M"

        return {
            "ticker": "LMT",
            "time_range": "1M",
            "period": "1mo",
            "count": 5,
            "data": [
                {"date": "2026-09-01", "close": 100.00},
                {"date": "2026-09-02", "close": 102.00},
                {"date": "2026-09-03", "close": 103.00},
                {"date": "2026-09-04", "close": 106.00},
                {"date": "2026-09-05", "close": None},
            ],
        }

    monkeypatch.setattr(
        "app.services.prediction_direction.get_historical_stock_data",
        fake_historical_stock_data,
    )

    result = get_prediction_direction("lmt")

    assert result["ticker"] == "LMT"
    assert result["as_of_date"] == "2026-09-04"
    assert result["prediction_direction"] == "UP"
    assert result["direction_label"] == "Upward"
    assert result["current_price"] == 106.00
    assert result["predicted_price"] == 108.00
    assert result["predicted_change"] == 2.00
    assert result["predicted_percent_change"] == 1.89
    assert result["prediction_confidence"] == 71.0
    assert result["prediction_uncertainty"] == 29.0
    assert result["confidence_label"] == "High confidence"


def test_prediction_direction_requires_at_least_two_closes(monkeypatch):
    def fake_historical_stock_data(ticker, time_range):
        return {
            "ticker": "LMT",
            "time_range": "1M",
            "period": "1mo",
            "count": 1,
            "data": [
                {"date": "2026-09-01", "close": 100.00},
            ],
        }

    monkeypatch.setattr(
        "app.services.prediction_direction.get_historical_stock_data",
        fake_historical_stock_data,
    )

    with pytest.raises(PredictionDirectionError):
        get_prediction_direction("LMT")

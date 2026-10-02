import pytest

from app.services.stock_prediction import (
    StockPredictionError,
    get_stock_prediction,
    prepare_prediction_data,
    train_and_predict,
)


def sample_records():
    return [
        {
            "date": "2026-01-01",
            "open": 100,
            "high": 105,
            "low": 99,
            "close": 103,
            "volume": 1000,
        },
        {
            "date": "2026-01-02",
            "open": 103,
            "high": 107,
            "low": 102,
            "close": 106,
            "volume": 1100,
        },
        {
            "date": "2026-01-03",
            "open": 106,
            "high": 109,
            "low": 104,
            "close": 108,
            "volume": 1200,
        },
        {
            "date": "2026-01-04",
            "open": 108,
            "high": 111,
            "low": 107,
            "close": 110,
            "volume": 1300,
        },
        {
            "date": "2026-01-05",
            "open": 110,
            "high": 114,
            "low": 109,
            "close": 113,
            "volume": 1400,
        },
        {
            "date": "2026-01-06",
            "open": 113,
            "high": 116,
            "low": 111,
            "close": 115,
            "volume": 1500,
        },
    ]


def test_prepare_prediction_data_creates_features_and_targets():
    features, targets, dates = prepare_prediction_data(sample_records())

    assert features.shape == (5, 5)
    assert targets.tolist() == [106.0, 108.0, 110.0, 113.0, 115.0]
    assert dates == [
        "2026-01-02",
        "2026-01-03",
        "2026-01-04",
        "2026-01-05",
        "2026-01-06",
    ]


def test_train_and_predict_returns_aligned_predictions():
    result = train_and_predict(sample_records(), train_ratio=0.6)

    assert result["model"] == "LinearRegression"
    assert result["training_count"] == 3
    assert result["test_count"] == 2

    assert result["dates"] == [
        "2026-01-05",
        "2026-01-06",
    ]

    assert len(result["actual"]) == 2
    assert len(result["predictions"]) == 2


def test_prediction_uses_chronological_split():
    result = train_and_predict(sample_records(), train_ratio=0.6)

    assert result["actual"] == [113.0, 115.0]
    assert result["dates"][0] == "2026-01-05"


def test_prepare_prediction_data_requires_enough_records():
    with pytest.raises(ValueError):
        prepare_prediction_data(
            [
                {
                    "date": "2026-01-01",
                    "open": 100,
                    "high": 101,
                    "low": 99,
                    "close": 100,
                    "volume": 1000,
                }
            ]
        )


def test_prepare_prediction_data_rejects_missing_fields():
    records = sample_records()
    del records[0]["volume"]

    with pytest.raises(ValueError):
        prepare_prediction_data(records)


def test_train_and_predict_rejects_invalid_ratio():
    with pytest.raises(ValueError):
        train_and_predict(sample_records(), train_ratio=1.0)


def test_train_and_predict_rejects_split_with_no_test_data():
    with pytest.raises(StockPredictionError):
        train_and_predict(
            sample_records()[:3],
            train_ratio=0.99,
        )


def test_get_stock_prediction_uses_historical_pipeline(monkeypatch):
    records = sample_records()

    def fake_historical_stock_data(ticker, time_range):
        assert ticker == "LMT"
        assert time_range == "1Y"

        return {
            "ticker": "LMT",
            "time_range": "1Y",
            "period": "1y",
            "count": len(records),
            "data": records,
        }

    monkeypatch.setattr(
        "app.services.stock_prediction.get_historical_stock_data",
        fake_historical_stock_data,
    )

    result = get_stock_prediction("lmt")

    assert result["ticker"] == "LMT"
    assert result["model"] == "LinearRegression"
    assert len(result["actual"]) == len(result["predictions"])
    assert result["test_count"] == len(result["actual"])


def test_get_stock_prediction_handles_invalid_historical_data(monkeypatch):
    def fake_historical_stock_data(ticker, time_range):
        return {
            "ticker": ticker,
            "data": [
                {
                    "date": "2026-01-01",
                    "open": 100,
                    "high": 101,
                    "low": 99,
                    "close": 100,
                    "volume": 1000,
                }
            ],
        }

    monkeypatch.setattr(
        "app.services.stock_prediction.get_historical_stock_data",
        fake_historical_stock_data,
    )

    with pytest.raises(StockPredictionError):
        get_stock_prediction("LMT")

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from app.services.historical_stock_data import (
    HistoricalStockDataError,
    calculate_risk_metrics,
    get_historical_stock_data,
)


def make_history_dataframe():
    return pd.DataFrame(
        {
            "Open": [480.25, 485.50],
            "High": [487.10, 490.20],
            "Low": [478.90, 483.75],
            "Close": [485.50, 488.90],
            "Volume": [1200000, 1350000],
        },
        index=pd.to_datetime(["2026-09-08", "2026-09-09"]),
    )


def test_empty_ticker_raises_value_error():
    with pytest.raises(ValueError):
        get_historical_stock_data("", "1Y")


def test_invalid_time_range_raises_value_error():
    with pytest.raises(ValueError):
        get_historical_stock_data("LMT", "17Y")


def test_calculate_risk_metrics_from_daily_prices():
    metrics = calculate_risk_metrics([100, 110, 99, 108.9], "close")

    assert metrics["price_basis"] == "close"
    assert metrics["price_observations"] == 4
    assert metrics["daily_return_observations"] == 3
    assert metrics["period_return"] == pytest.approx(0.089)
    assert metrics["annualized_volatility"] == pytest.approx(1.83303027798)
    assert metrics["max_drawdown"] == pytest.approx(-0.1)
    assert metrics["best_daily_return"] == pytest.approx(0.1)
    assert metrics["worst_daily_return"] == pytest.approx(-0.1)


def test_volatility_is_unavailable_with_fewer_than_two_daily_returns():
    metrics = calculate_risk_metrics([100, 110], "close")

    assert metrics["period_return"] == pytest.approx(0.1)
    assert metrics["annualized_volatility"] is None


@patch("app.services.historical_stock_data.yf.Ticker")
def test_time_range_is_normalized_and_mapped(mock_ticker):
    mock_stock = Mock()
    mock_stock.history.return_value = make_history_dataframe()
    mock_ticker.return_value = mock_stock

    result = get_historical_stock_data("lmt", "1y")

    mock_stock.history.assert_called_once_with(
        period="1y",
        interval="1d",
        auto_adjust=False,
    )

    assert result["ticker"] == "LMT"
    assert result["time_range"] == "1Y"
    assert result["period"] == "1y"
    assert result["count"] == 2


@patch("app.services.historical_stock_data.yf.Ticker")
def test_historical_records_are_formatted_correctly(mock_ticker):
    mock_stock = Mock()
    mock_stock.history.return_value = make_history_dataframe()
    mock_ticker.return_value = mock_stock

    result = get_historical_stock_data("LMT", "1M")

    assert result["data"][0] == {
        "date": "2026-09-08",
        "open": 480.25,
        "high": 487.10,
        "low": 478.90,
        "close": 485.50,
        "volume": 1200000,
    }

    assert result["data"][1]["close"] == 488.90
    assert result["data"][1]["volume"] == 1350000


@patch("app.services.historical_stock_data.yf.Ticker")
def test_risk_metrics_use_adjusted_close_when_available(mock_ticker):
    mock_stock = Mock()
    mock_stock.history.return_value = pd.DataFrame(
        {
            "Open": [99.0, 79.0, 109.0],
            "High": [101.0, 81.0, 111.0],
            "Low": [98.0, 78.0, 108.0],
            "Close": [100.0, 80.0, 110.0],
            "Adj Close": [100.0, 95.0, 110.0],
            "Volume": [1000, 1100, 1200],
        },
        index=pd.to_datetime(["2026-09-08", "2026-09-09", "2026-09-10"]),
    )
    mock_ticker.return_value = mock_stock

    result = get_historical_stock_data("LMT", "1M")

    assert result["risk_metrics"]["price_basis"] == "adjusted_close"
    assert result["risk_metrics"]["period_return"] == pytest.approx(0.1)
    assert result["risk_metrics"]["max_drawdown"] == pytest.approx(-0.05)


@patch("app.services.historical_stock_data.yf.Ticker")
def test_empty_history_raises_historical_stock_data_error(mock_ticker):
    mock_stock = Mock()
    mock_stock.history.return_value = pd.DataFrame()
    mock_ticker.return_value = mock_stock

    with pytest.raises(HistoricalStockDataError):
        get_historical_stock_data("LMT", "6M")

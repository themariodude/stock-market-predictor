from unittest.mock import Mock, patch

import pandas as pd
import pytest

from app.services.historical_stock_data import (
    HistoricalStockDataError,
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
def test_empty_history_raises_historical_stock_data_error(mock_ticker):
    mock_stock = Mock()
    mock_stock.history.return_value = pd.DataFrame()
    mock_ticker.return_value = mock_stock

    with pytest.raises(HistoricalStockDataError):
        get_historical_stock_data("LMT", "6M")

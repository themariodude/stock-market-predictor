from unittest.mock import Mock, patch

import pytest

from app.services.current_stock_info import (
    StockDataError,
    get_current_stock_info,
)


def test_empty_ticker_raises_value_error():
    with pytest.raises(ValueError):
        get_current_stock_info("")


@patch("app.services.current_stock_info.yf.Ticker")
def test_current_stock_info_returns_expected_values(mock_ticker):
    mock_stock = Mock()
    mock_stock.fast_info = {
        "last_price": 500.25,
        "previous_close": 495.00,
        "last_volume": 1234567,
    }
    mock_ticker.return_value = mock_stock

    result = get_current_stock_info("lmt")

    assert result["ticker"] == "LMT"
    assert result["current_price"] == 500.25
    assert result["previous_close"] == 495.00
    assert result["price_change"] == 5.25
    assert result["percent_change"] == 1.06
    assert result["volume"] == 1234567


@patch("app.services.current_stock_info.yf.Ticker")
def test_missing_current_price_raises_stock_data_error(mock_ticker):
    mock_stock = Mock()
    mock_stock.fast_info = {
        "last_price": None,
        "previous_close": 495.00,
        "last_volume": 1234567,
    }
    mock_ticker.return_value = mock_stock

    with pytest.raises(StockDataError):
        get_current_stock_info("LMT")

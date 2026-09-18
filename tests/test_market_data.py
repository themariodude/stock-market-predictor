import pandas as pd
import pytest
from unittest.mock import patch

from src.data.market_data import YFinanceProvider


def make_valid_dataframe():
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [105.0, 106.0],
            "Low": [99.0, 100.0],
            "Close": [104.0, 105.0],
            "Adj Close": [104.0, 105.0],
            "Volume": [1_000_000, 1_100_000],
        },
        index=pd.to_datetime(["2026-01-02", "2026-01-05"]),
    ).rename_axis("Date")


@patch("src.data.market_data.yf.download")
def test_fetch_historical_data_returns_normalized_dataframe(mock_download):
    mock_download.return_value = make_valid_dataframe()

    provider = YFinanceProvider()

    result = provider.fetch_historical_data(
        ticker="LMT",
        start_date="2026-01-01",
        end_date="2026-01-10",
    )

    assert list(result.columns) == [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    assert len(result) == 2
    assert pd.api.types.is_datetime64_any_dtype(result["date"])


def test_empty_ticker_raises_value_error():
    provider = YFinanceProvider()

    with pytest.raises(ValueError, match="Ticker symbol must be a non-empty string"):
        provider.fetch_historical_data(
            ticker="",
            start_date="2026-01-01",
            end_date="2026-01-10",
        )


def test_invalid_date_range_raises_value_error():
    provider = YFinanceProvider()

    with pytest.raises(ValueError, match="start_date must be earlier than end_date"):
        provider.fetch_historical_data(
            ticker="LMT",
            start_date="2026-01-10",
            end_date="2026-01-01",
        )


@patch("src.data.market_data.yf.download")
def test_empty_dataframe_raises_value_error(mock_download):
    mock_download.return_value = pd.DataFrame()

    provider = YFinanceProvider()

    with pytest.raises(ValueError, match="No data returned"):
        provider.fetch_historical_data(
            ticker="LMT",
            start_date="2026-01-01",
            end_date="2026-01-10",
        )


@patch("src.data.market_data.yf.download")
def test_missing_required_columns_raises_key_error(mock_download):
    mock_download.return_value = pd.DataFrame(
        {
            "Open": [100.0],
            "Close": [104.0],
        },
        index=pd.to_datetime(["2026-01-02"]),
    ).rename_axis("Date")

    provider = YFinanceProvider()

    with pytest.raises(KeyError, match="Missing expected columns"):
        provider.fetch_historical_data(
            ticker="LMT",
            start_date="2026-01-01",
            end_date="2026-01-10",
        )
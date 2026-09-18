import pandas as pd
import pytest

from src.data.data_cleaner import MarketDataCleaner


def make_valid_dataframe():
    """Create valid sample market data for cleaner tests."""
    return pd.DataFrame(
        {
            "date": ["2026-01-03", "2026-01-01", "2026-01-02"],
            "open": [103.0, 100.0, 101.0],
            "high": [106.0, 105.0, 104.0],
            "low": [101.0, 99.0, 100.0],
            "close": [105.0, 104.0, 103.0],
            "volume": [1_300_000, 1_000_000, 1_100_000],
        }
    )


def test_clean_valid_data_returns_sorted_dataframe():
    cleaner = MarketDataCleaner()

    result = cleaner.clean(make_valid_dataframe())

    assert list(result.columns) == [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert len(result) == 3
    assert result["date"].is_monotonic_increasing
    assert list(result.index) == [0, 1, 2]


def test_missing_required_column_raises_key_error():
    cleaner = MarketDataCleaner()
    df = make_valid_dataframe().drop(columns=["volume"])

    with pytest.raises(KeyError, match="Missing required columns"):
        cleaner.clean(df)


def test_duplicate_dates_are_removed():
    cleaner = MarketDataCleaner()
    df = make_valid_dataframe()

    duplicate = df.iloc[[0]].copy()
    df = pd.concat([df, duplicate], ignore_index=True)

    result = cleaner.clean(df)

    assert len(result) == 3
    assert not result["date"].duplicated().any()


def test_missing_required_value_is_removed():
    cleaner = MarketDataCleaner()
    df = make_valid_dataframe()
    df.loc[0, "close"] = None

    result = cleaner.clean(df)

    assert len(result) == 2
    assert not result["close"].isna().any()


def test_malformed_numeric_value_raises_value_error():
    cleaner = MarketDataCleaner()
    df = make_valid_dataframe()

    # Object dtype allows us to simulate malformed provider data.
    df["close"] = df["close"].astype(object)
    df.loc[0, "close"] = "not-a-number"

    with pytest.raises(
        ValueError,
        match="Column 'close' contains non-numeric values",
    ):
        cleaner.clean(df)


def test_invalid_date_raises_value_error():
    cleaner = MarketDataCleaner()
    df = make_valid_dataframe()
    df.loc[0, "date"] = "not-a-date"

    with pytest.raises(
        ValueError,
        match="Column 'date' contains invalid date values",
    ):
        cleaner.clean(df)


def test_negative_volume_raises_value_error():
    cleaner = MarketDataCleaner()
    df = make_valid_dataframe()
    df.loc[0, "volume"] = -1

    with pytest.raises(ValueError, match="Volume cannot be negative"):
        cleaner.clean(df)


def test_negative_price_raises_value_error():
    cleaner = MarketDataCleaner()
    df = make_valid_dataframe()
    df.loc[0, "open"] = -5.0

    with pytest.raises(ValueError, match="Price values cannot be negative"):
        cleaner.clean(df)


def test_high_lower_than_low_raises_value_error():
    cleaner = MarketDataCleaner()
    df = make_valid_dataframe()
    df.loc[0, "high"] = 90.0
    df.loc[0, "low"] = 100.0

    with pytest.raises(
        ValueError,
        match="High price cannot be lower than low price",
    ):
        cleaner.clean(df)


def test_open_outside_daily_range_raises_value_error():
    cleaner = MarketDataCleaner()
    df = make_valid_dataframe()
    df.loc[0, "open"] = 110.0

    with pytest.raises(
        ValueError,
        match="Open price must fall within the daily high/low range",
    ):
        cleaner.clean(df)


def test_close_outside_daily_range_raises_value_error():
    cleaner = MarketDataCleaner()
    df = make_valid_dataframe()
    df.loc[0, "close"] = 110.0

    with pytest.raises(
        ValueError,
        match="Close price must fall within the daily high/low range",
    ):
        cleaner.clean(df)
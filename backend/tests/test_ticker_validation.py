import pytest

from app.services.ticker_validation import (
    SUPPORTED_TICKERS,
    UnsupportedTickerError,
    is_supported_ticker,
    normalize_ticker,
    validate_ticker,
)


def test_supported_tickers_are_correct():
    expected_tickers = {
        "LMT",
        "RTX",
        "NOC",
        "GD",
        "LHX",
        "BA",
    }

    assert SUPPORTED_TICKERS == expected_tickers


@pytest.mark.parametrize(
    "ticker",
    [
        "LMT",
        "RTX",
        "NOC",
        "GD",
        "LHX",
        "BA",
    ],
)
def test_supported_tickers_are_valid(ticker):
    assert is_supported_ticker(ticker) is True


@pytest.mark.parametrize(
    ("ticker", "expected"),
    [
        ("lmt", "LMT"),
        ("LmT", "LMT"),
        ("  lmt  ", "LMT"),
        ("rtx", "RTX"),
        (" NOC ", "NOC"),
    ],
)
def test_normalize_ticker(ticker, expected):
    assert normalize_ticker(ticker) == expected


@pytest.mark.parametrize(
    "ticker",
    [
        "INVALID",
        "AAPL",
        "MSFT",
        "123",
        "!!!",
        "",
        "   ",
    ],
)
def test_unsupported_tickers_are_invalid(ticker):
    assert is_supported_ticker(ticker) is False


@pytest.mark.parametrize(
    ("ticker", "expected"),
    [
        ("LMT", "LMT"),
        ("lmt", "LMT"),
        (" LmT ", "LMT"),
        ("rtx", "RTX"),
        ("  NOC  ", "NOC"),
    ],
)
def test_validate_ticker_returns_normalized_ticker(ticker, expected):
    assert validate_ticker(ticker) == expected


@pytest.mark.parametrize(
    "ticker",
    [
        "INVALID",
        "AAPL",
        "123",
        "!!!",
        "",
        "   ",
    ],
)
def test_validate_ticker_raises_for_unsupported_ticker(ticker):
    with pytest.raises(UnsupportedTickerError):
        validate_ticker(ticker)


def test_unsupported_ticker_error_contains_ticker():
    with pytest.raises(
        UnsupportedTickerError,
        match="Unsupported ticker: AAPL",
    ):
        validate_ticker("AAPL")


def test_unsupported_ticker_error_is_value_error():
    assert issubclass(UnsupportedTickerError, ValueError)
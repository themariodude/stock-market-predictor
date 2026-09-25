"""Utilities for validating supported stock ticker symbols."""

SUPPORTED_TICKERS = frozenset(
    {
        "LMT",
        "RTX",
        "NOC",
        "GD",
        "LHX",
        "BA",
    }
)


class UnsupportedTickerError(ValueError):
    """Raised when a ticker is not supported by the application."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(f"Unsupported ticker: {ticker}")


def normalize_ticker(ticker: str) -> str:
    """
    Normalize a ticker symbol.

    Leading and trailing whitespace is removed and the ticker is converted
    to uppercase.
    """
    return ticker.strip().upper()


def is_supported_ticker(ticker: str) -> bool:
    """
    Return True when the ticker is supported by the application.

    The ticker is normalized before validation.
    """
    normalized_ticker = normalize_ticker(ticker)

    if not normalized_ticker:
        return False

    return normalized_ticker in SUPPORTED_TICKERS


def validate_ticker(ticker: str) -> str:
    """
    Validate and normalize a ticker.
    """
    normalized_ticker = normalize_ticker(ticker)

    if not normalized_ticker or normalized_ticker not in SUPPORTED_TICKERS:
        raise UnsupportedTickerError(normalized_ticker or ticker)

    return normalized_ticker
"""
US-03 — View Current Stock Information

Provides recent stock information including:
- Current price
- Previous closing price
- Price change
- Percentage price change
- Trading volume

This service is designed to be imported by the FastAPI backend.
"""

from typing import Any

import yfinance as yf


class StockDataError(Exception):
    """Raised when current stock information cannot be retrieved."""


def get_current_stock_info(ticker: str) -> dict[str, Any]:
    """
    Retrieve current information for a stock ticker.

    Args:
        ticker: Stock ticker symbol, such as "LMT".

    Returns:
        Dictionary containing:
        - ticker
        - current_price
        - previous_close
        - price_change
        - percent_change
        - volume

    Raises:
        ValueError: If the ticker is empty.
        StockDataError: If market data cannot be retrieved.
    """
    if not ticker or not ticker.strip():
        raise ValueError("Ticker symbol is required.")

    symbol = ticker.strip().upper()

    try:
        stock = yf.Ticker(symbol)
        info = stock.fast_info

        current_price = info.get("last_price")
        previous_close = info.get("previous_close")
        volume = info.get("last_volume")

        if current_price is None:
           raise StockDataError(f"Current price could not be retrieved for {symbol}.")

        price_change = None
        percent_change = None

        if previous_close is not None and previous_close != 0:
            price_change = current_price - previous_close
            percent_change = (price_change / previous_close) * 100

        return {
            "ticker": symbol,
            "current_price": round(float(current_price), 2),
            "previous_close": (
                round(float(previous_close), 2) if previous_close is not None else None
            ),
            "price_change": (
                round(float(price_change), 2) if price_change is not None else None
            ),
            "percent_change": (
                round(float(percent_change), 2) if percent_change is not None else None
            ),
            "volume": int(volume) if volume is not None else None,
        }

    except StockDataError:
        raise
    except Exception as exc:
        raise StockDataError(
            f"Unable to retrieve stock information for {symbol}."
        ) from exc

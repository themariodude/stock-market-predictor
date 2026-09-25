"""
US-04 — Change Historical Time Range

Provides historical stock data for a selected time range.
"""

from typing import Any
import yfinance as yf


class HistoricalStockDataError(Exception):
    """Raised when historical stock data cannot be retrieved."""


TIME_RANGE_TO_YFINANCE_PERIOD = {
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "5Y": "5y",
    "MAX": "max",
}


def get_historical_stock_data(ticker: str, time_range: str) -> dict[str, Any]:
    """Retrieve historical stock data for a supported time range."""
    if not ticker or not ticker.strip():
        raise ValueError("Ticker symbol is required.")

    if not time_range or not time_range.strip():
        raise ValueError("Historical time range is required.")

    symbol = ticker.strip().upper()
    normalized_range = time_range.strip().upper()

    if normalized_range not in TIME_RANGE_TO_YFINANCE_PERIOD:
        supported = ", ".join(TIME_RANGE_TO_YFINANCE_PERIOD.keys())
        raise ValueError(
            f"Unsupported time range '{time_range}'. "
            f"Supported ranges are: {supported}."
        )

    period = TIME_RANGE_TO_YFINANCE_PERIOD[normalized_range]

    try:
        stock = yf.Ticker(symbol)
        history = stock.history(period=period, interval="1d", auto_adjust=False)

        if history is None or history.empty:
            raise HistoricalStockDataError(
                f"No historical data was returned for {symbol} "
                f"using time range {normalized_range}."
            )

        records = []
        for index, row in history.iterrows():
            records.append(
                {
                    "date": index.date().isoformat(),
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                }
            )

        return {
            "ticker": symbol,
            "time_range": normalized_range,
            "period": period,
            "count": len(records),
            "data": records,
        }

    except HistoricalStockDataError:
        raise
    except Exception as exc:
        raise HistoricalStockDataError(
            f"Unable to retrieve historical stock data for {symbol}."
        ) from exc

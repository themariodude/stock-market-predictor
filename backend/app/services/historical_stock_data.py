"""
US-04 — Change Historical Time Range

Provides historical stock data for a selected time range.
"""

import math
from statistics import stdev
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


def calculate_risk_metrics(prices: list[float], price_basis: str) -> dict[str, Any]:
    """Calculate period return and daily-return risk measures from prices."""
    valid_prices = [price for price in prices if math.isfinite(price) and price > 0]
    daily_returns = [
        current / previous - 1
        for previous, current in zip(valid_prices, valid_prices[1:])
    ]

    peak = None
    drawdowns = []
    for price in valid_prices:
        peak = price if peak is None else max(peak, price)
        drawdowns.append(price / peak - 1)

    annualized_volatility = (
        stdev(daily_returns) * math.sqrt(252) if len(daily_returns) >= 2 else None
    )

    return {
        "price_basis": price_basis,
        "price_observations": len(valid_prices),
        "daily_return_observations": len(daily_returns),
        "period_return": (
            valid_prices[-1] / valid_prices[0] - 1 if len(valid_prices) >= 2 else None
        ),
        "annualized_volatility": annualized_volatility,
        "max_drawdown": min(drawdowns) if drawdowns else None,
        "best_daily_return": max(daily_returns) if daily_returns else None,
        "worst_daily_return": min(daily_returns) if daily_returns else None,
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
            f"Unsupported time range '{time_range}'. Supported ranges are: {supported}."
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

        price_column = "Adj Close" if "Adj Close" in history.columns else "Close"
        risk_prices = [float(value) for value in history[price_column]]

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
            "risk_metrics": calculate_risk_metrics(
                risk_prices,
                "adjusted_close" if price_column == "Adj Close" else "close",
            ),
            "data": records,
        }

    except HistoricalStockDataError:
        raise
    except Exception as exc:
        raise HistoricalStockDataError(
            f"Unable to retrieve historical stock data for {symbol}."
        ) from exc

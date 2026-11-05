from datetime import date
from math import isfinite
from typing import Any

BENCHMARK_TICKER = "SPY"
SUPPORTED_STOCKS = frozenset({"LMT", "RTX", "NOC", "GD", "LHX", "BA"})


def get_historical_stock_data(ticker: str, time_range: str) -> dict[str, Any]:
    """Delegate to the existing provider (lazy import for isolated tests)."""
    from app.services.historical_stock_data import get_historical_stock_data as fetch

    return fetch(ticker, time_range)


def _prices_by_date(history: dict[str, Any]) -> dict[date, float]:
    prices = {}

    for record in history["data"]:
        day = date.fromisoformat(record["date"])
        price = float(record["close"])

        if not isfinite(price) or price <= 0:
            raise ValueError(
                "Historical closing prices must be positive and finite."
            )

        if day in prices:
            raise ValueError("Duplicate historical trading date.")

        prices[day] = price

    return prices


def compare_stock_against_spy(
    ticker: str,
    time_range: str = "1Y",
) -> dict[str, Any]:
    """Compare total returns over the same first/last shared trading dates.

    Uses unadjusted closes provided by the existing historical-data service;
    dividends and distributions are not included in returns.
    """

    symbol = ticker.strip().upper() if isinstance(ticker, str) else ""

    if symbol not in SUPPORTED_STOCKS:
        raise ValueError("Unsupported defense stock ticker.")

    stock = get_historical_stock_data(symbol, time_range)
    benchmark = get_historical_stock_data(BENCHMARK_TICKER, time_range)

    stock_prices = _prices_by_date(stock)
    benchmark_prices = _prices_by_date(benchmark)

    shared_dates = sorted(stock_prices.keys() & benchmark_prices.keys())

    if len(shared_dates) < 2:
        raise ValueError("At least two shared trading dates are required.")

    first, last = shared_dates[0], shared_dates[-1]

    stock_return = (
        stock_prices[last] / stock_prices[first] - 1
    ) * 100

    benchmark_return = (
        benchmark_prices[last] / benchmark_prices[first] - 1
    ) * 100

    excess = stock_return - benchmark_return

    status = (
        "MATCHED" if abs(excess) < 1e-9
        else "OUTPERFORMED" if excess > 0
        else "UNDERPERFORMED"
    )

    return {
        "ticker": symbol,
        "benchmark": BENCHMARK_TICKER,
        "time_range": stock["time_range"],
        "start_date": first.isoformat(),
        "end_date": last.isoformat(),
        "shared_trading_days": len(shared_dates),
        "stock_return_pct": round(stock_return, 4),
        "benchmark_return_pct": round(benchmark_return, 4),
        "excess_return_percentage_points": round(excess, 4),
        "status": status,
        "price_basis": "unadjusted_close_excludes_dividends",
    }

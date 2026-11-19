"""US-30 — Stock performance versus a market benchmark."""

import math

from fastapi import APIRouter, HTTPException, Query

from app.api.stocks import validate_supported_ticker
from app.services.historical_stock_data import (
    TIME_RANGE_TO_YFINANCE_PERIOD,
    HistoricalStockDataError,
    get_historical_stock_data,
)

router = APIRouter(prefix="/benchmark", tags=["benchmark"])

BENCHMARKS = {
    "SPY": "SPDR S&P 500 ETF Trust",
    "ITA": "iShares U.S. Aerospace & Defense ETF",
}


@router.get("/{ticker}")
def get_benchmark(
    ticker: str,
    time_range: str = Query(default="1Y"),
    benchmark: str = Query(default="SPY"),
) -> dict:
    """Compare a supported stock against a market benchmark."""
    symbol = validate_supported_ticker(ticker)
    normalized_range = time_range.strip().upper()
    benchmark_symbol = benchmark.strip().upper()

    if normalized_range not in TIME_RANGE_TO_YFINANCE_PERIOD:
        raise HTTPException(
            status_code=400,
            detail="Unsupported time range.",
        )

    if benchmark_symbol not in BENCHMARKS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported benchmark.",
        )

    try:
        stock_history = get_historical_stock_data(symbol, normalized_range)
        benchmark_history = get_historical_stock_data(
            benchmark_symbol, normalized_range
        )

        stock_prices = {
            record["date"]: float(record["close"]) for record in stock_history["data"]
        }
        benchmark_prices = {
            record["date"]: float(record["close"])
            for record in benchmark_history["data"]
        }

    except (HistoricalStockDataError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve benchmark comparison data.",
        ) from exc

    common_dates = sorted(stock_prices.keys() & benchmark_prices.keys())

    if len(common_dates) < 2:
        raise HTTPException(
            status_code=502,
            detail="Insufficient common historical data.",
        )

    if any(
        not math.isfinite(price) or price <= 0
        for date in common_dates
        for price in (stock_prices[date], benchmark_prices[date])
    ):
        raise HTTPException(
            status_code=502,
            detail="Invalid historical prices.",
        )

    first_date = common_dates[0]
    initial_stock = stock_prices[first_date]
    initial_benchmark = benchmark_prices[first_date]

    results = []

    for date in common_dates:
        stock_return = (stock_prices[date] / initial_stock - 1) * 100

        benchmark_return = (benchmark_prices[date] / initial_benchmark - 1) * 100

        results.append(
            {
                "date": date,
                "stock_return_pct": round(stock_return, 4),
                "benchmark_return_pct": round(benchmark_return, 4),
                "excess_return_pct": round(stock_return - benchmark_return, 4),
            }
        )

    return {
        "ticker": symbol,
        "benchmark": benchmark_symbol,
        "benchmark_name": BENCHMARKS[benchmark_symbol],
        "time_range": normalized_range,
        "methodology": "unadjusted_close_price_return",
        "count": len(results),
        "data": results,
    }

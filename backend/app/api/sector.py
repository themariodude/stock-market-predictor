"""US-30 — Defense-sector data and cumulative performance."""

import math

from fastapi import APIRouter, HTTPException, Query

from app.api.stocks import SUPPORTED_STOCKS
from app.services.historical_stock_data import (
    TIME_RANGE_TO_YFINANCE_PERIOD,
    HistoricalStockDataError,
    get_historical_stock_data,
)

router = APIRouter(prefix="/sector", tags=["sector"])


@router.get("/defense")
def get_defense_sector() -> dict:
    """Return the supported defense-sector companies."""
    stocks = [
        {
            "ticker": ticker,
            "company_name": company_name,
        }
        for ticker, company_name in SUPPORTED_STOCKS.items()
    ]

    return {
        "sector": "defense",
        "stocks": stocks,
        "count": len(stocks),
    }


@router.get("/defense/performance")
def get_defense_performance(
    time_range: str = Query(default="1Y"),
) -> dict:
    """Calculate equal-weighted cumulative sector price returns."""
    normalized_range = time_range.strip().upper()

    if normalized_range not in TIME_RANGE_TO_YFINANCE_PERIOD:
        raise HTTPException(
            status_code=400,
            detail="Unsupported time range.",
        )

    prices = {}

    for ticker in SUPPORTED_STOCKS:
        try:
            history = get_historical_stock_data(ticker, normalized_range)
            records = history["data"]

            prices[ticker] = {
                record["date"]: float(record["close"]) for record in records
            }
        except (
            HistoricalStockDataError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Historical data unavailable for {ticker}.",
            ) from exc

    common_dates = sorted(
        set.intersection(*(set(stock_prices) for stock_prices in prices.values()))
    )

    if len(common_dates) < 2:
        raise HTTPException(
            status_code=502,
            detail="Insufficient common historical data.",
        )

    first_date = common_dates[0]

    for ticker, stock_prices in prices.items():
        if any(
            not math.isfinite(stock_prices[date]) or stock_prices[date] <= 0
            for date in common_dates
        ):
            raise HTTPException(
                status_code=502,
                detail=f"Invalid historical prices for {ticker}.",
            )

    initial_prices = {
        ticker: stock_prices[first_date] for ticker, stock_prices in prices.items()
    }

    series = []

    for date in common_dates:
        stock_returns = {
            ticker: round(
                (stock_prices[date] / initial_prices[ticker] - 1) * 100,
                4,
            )
            for ticker, stock_prices in prices.items()
        }

        sector_return = sum(stock_returns.values()) / len(stock_returns)

        series.append(
            {
                "date": date,
                "cumulative_return_pct": round(sector_return, 4),
                "stock_returns_pct": stock_returns,
            }
        )

    return {
        "sector": "defense",
        "time_range": normalized_range,
        "methodology": "equal_weighted_unadjusted_price_return",
        "count": len(series),
        "data": series,
    }

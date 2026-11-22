"""Scheduled refresh of the stocks supported by the application."""

import asyncio
import logging
import os

from app.api.stocks import SUPPORTED_STOCKS
from app.database import SessionLocal
from app.services.historical_stock_data import (
    HistoricalStockDataError,
    get_historical_stock_data,
)
from app.services.stock_storage import store_stock_prices

log = logging.getLogger(__name__)
DEFAULT_REFRESH_INTERVAL_SECONDS = 24 * 60 * 60


def refresh_market_data() -> None:
    """Fetch and persist the latest year of daily prices for supported stocks."""
    if SessionLocal is None:
        log.warning("Market data refresh skipped: DATABASE_URL is not configured.")
        return

    for ticker, company_name in SUPPORTED_STOCKS.items():
        try:
            history = get_historical_stock_data(ticker, "1Y")
            with SessionLocal() as session:
                store_stock_prices(session, ticker, company_name, history["data"])
            log.info(
                "Refreshed market data for %s (%d rows).",
                ticker,
                history["count"],
            )
        except (HistoricalStockDataError, KeyError, TypeError, ValueError):
            log.exception("Market data refresh failed for %s.", ticker)
        except Exception:
            # One provider or database failure must not stop later tickers.
            log.exception("Unexpected market data refresh failure for %s.", ticker)


async def run_market_data_refresh(interval_seconds: int) -> None:
    """Refresh immediately on startup, then repeat at the configured interval."""
    while True:
        await asyncio.to_thread(refresh_market_data)
        await asyncio.sleep(interval_seconds)


def get_refresh_interval_seconds() -> int:
    """Read a positive refresh interval from the environment."""
    raw_interval = os.getenv(
        "MARKET_DATA_REFRESH_INTERVAL_SECONDS",
        str(DEFAULT_REFRESH_INTERVAL_SECONDS),
    )
    try:
        interval = int(raw_interval)
    except ValueError as exc:
        raise ValueError(
            "MARKET_DATA_REFRESH_INTERVAL_SECONDS must be a positive integer."
        ) from exc
    if interval <= 0:
        raise ValueError(
            "MARKET_DATA_REFRESH_INTERVAL_SECONDS must be a positive integer."
        )
    return interval

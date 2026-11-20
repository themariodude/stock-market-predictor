"""US-41: Load prices for a verified trading session."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

from app.services.historical_stock_data import get_historical_stock_data
from app.services.market_alert_monitor import valid_price

HistoryLoader = Callable[[str, str], dict[str, Any]]


def get_verified_close_quote(
    ticker: str,
    session_date: date,
    history_loader: HistoryLoader = get_historical_stock_data,
) -> dict[str, Decimal] | None:
    """Return closing prices only when the latest session matches.

    The previous record represents the preceding trading session,
    which may be several calendar days earlier.
    """

    history = history_loader(ticker, "1M")
    records = history.get("data")

    if not isinstance(records, list) or len(records) < 2:
        return None

    previous, latest = records[-2:]

    if not isinstance(previous, dict) or not isinstance(latest, dict):
        return None

    try:
        previous_date = date.fromisoformat(previous["date"])
        latest_date = date.fromisoformat(latest["date"])
    except (KeyError, TypeError, ValueError):
        return None

    # Reject stale, future-dated, or incorrectly ordered records.
    if latest_date != session_date or previous_date >= latest_date:
        return None

    observed_price = valid_price(latest.get("close"))
    reference_price = valid_price(previous.get("close"))

    if observed_price is None or reference_price is None:
        return None

    return {
        "current_price": observed_price,
        "previous_close": reference_price,
    }

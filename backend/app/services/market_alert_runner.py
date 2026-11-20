"""US-41: Run market alert scans using verified closing prices."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.services.historical_stock_data import get_historical_stock_data
from app.services.market_alert_monitor import scan_market_alerts
from app.services.market_session_prices import get_verified_close_quote

HistoryLoader = Callable[[str, str], dict[str, Any]]


def run_verified_market_scan(
    db: Session,
    session_date: date,
    *,
    history_loader: HistoryLoader = get_historical_stock_data,
) -> int:
    """Evaluate active alerts using verified session closing prices."""

    def load_verified_price(
        ticker: str,
    ) -> dict[str, Decimal] | None:
        return get_verified_close_quote(
            ticker,
            session_date,
            history_loader=history_loader,
        )

    return scan_market_alerts(
        db,
        trading_date=session_date,
        price_loader=load_verified_price,
    )

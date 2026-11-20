"""US-41: Detect significant market changes and create notifications."""

import logging
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.market_alert import MarketAlert
from app.models.notification_event import NotificationEvent
from app.services.current_stock_info import get_current_stock_info

log = logging.getLogger(__name__)

PriceLoader = Callable[[str], dict[str, Any]]


def valid_price(value: object) -> Decimal | None:
    """Return a positive finite price, or None for unusable data."""
    try:
        if value is None:
            return None
        price = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None

    if not price.is_finite() or price <= 0:
        return None

    return price


def threshold_reached(
    change_percent: Decimal,
    threshold_percent: Decimal,
    direction: str,
) -> bool:
    """Determine whether a price change satisfies an alert."""
    if direction == "increase":
        return change_percent >= threshold_percent

    if direction == "decrease":
        return change_percent <= -threshold_percent

    if direction == "either":
        return abs(change_percent) >= threshold_percent

    return False


def scan_market_alerts(
    db: Session,
    trading_date: date,
    price_loader: PriceLoader = get_current_stock_info,
) -> int:
    """Scan active alerts and persist matching notifications.

    trading_date must be a verified market-session date supplied
    by the future scheduler, not simply the machine's local date.
    """

    alerts = db.scalars(
        select(MarketAlert)
        .where(MarketAlert.is_active.is_(True))
        .order_by(MarketAlert.id)
    ).all()

    price_cache: dict[str, dict[str, Any] | None] = {}
    created_count = 0

    for alert in alerts:
        ticker = alert.ticker.upper()

        # Fetch each ticker only once per scan.
        if ticker not in price_cache:
            try:
                price_cache[ticker] = price_loader(ticker)
            except Exception:
                log.exception("Unable to retrieve market data for %s", ticker)
                price_cache[ticker] = None

        quote = price_cache[ticker]

        if quote is None:
            continue

        current_price = valid_price(quote.get("current_price"))
        previous_close = valid_price(quote.get("previous_close"))

        # Never trigger alerts using missing or invalid prices.
        if current_price is None or previous_close is None:
            log.warning("Skipping %s: missing or invalid prices", ticker)
            continue

        change_percent = (
            (current_price - previous_close) / previous_close * Decimal("100")
        )

        if not threshold_reached(
            change_percent,
            Decimal(str(alert.threshold_percent)),
            alert.direction,
        ):
            continue

        # One notification per alert per trading session.
        dedup_key = f"alert:{alert.id}:date:{trading_date.isoformat()}"

        existing = db.scalar(
            select(NotificationEvent.id).where(
                NotificationEvent.deduplication_key == dedup_key
            )
        )

        if existing is not None:
            continue

        notification = NotificationEvent(
            alert_id=alert.id,
            user_id=alert.user_id,
            ticker=ticker,
            threshold_percent=alert.threshold_percent,
            observed_change_percent=change_percent.quantize(Decimal("0.0001")),
            observed_price=current_price,
            reference_price=previous_close,
            deduplication_key=dedup_key,
            is_read=False,
        )

        db.add(notification)

        try:
            db.commit()
            created_count += 1
            log.info("Created market alert notification for %s", ticker)
        except IntegrityError:
            # The unique key also prevents duplicates if two
            # workers attempt to create the same notification.
            db.rollback()
            log.warning(
                "Notification insert conflict for %s",
                dedup_key,
            )

    return created_count

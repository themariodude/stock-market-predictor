"""US-41: Independent scheduled market-monitoring worker."""

import logging
import time
from collections.abc import Callable
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.database import get_session
from app.services.market_alert_runner import run_verified_market_scan

log = logging.getLogger(__name__)

MARKET_TIMEZONE = ZoneInfo("America/New_York")
CHECK_INTERVAL_SECONDS = 3600
START_HOUR = 18


def get_monitoring_date(now: datetime) -> date | None:
    """Return the US market date when monitoring is allowed."""
    if now.tzinfo is None:
        raise ValueError("Monitoring requires a timezone-aware datetime.")

    eastern = now.astimezone(MARKET_TIMEZONE)

    # Saturday and Sunday.
    if eastern.weekday() >= 5:
        return None

    # Wait until after the regular market session has ended.
    if eastern.hour < START_HOUR:
        return None

    return eastern.date()


def run_monitoring_cycle(
    now: datetime,
    session_factory: Callable[[], Session] = get_session,
    scanner: Callable[[Session, date], int] = run_verified_market_scan,
) -> int:
    """Run one verified market scan when monitoring is due."""
    session_date = get_monitoring_date(now)

    if session_date is None:
        return 0

    with session_factory() as db:
        return scanner(db, session_date)


def main() -> None:
    """Continuously check for completed market sessions."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    log.info("US-41 market monitor worker started.")

    while True:
        now = datetime.now(timezone.utc)

        try:
            session_date = get_monitoring_date(now)

            if session_date is not None:
                count = run_monitoring_cycle(now)

                log.info(
                    "Market scan completed for %s: %s notifications created.",
                    session_date,
                    count,
                )

        except Exception:
            # A temporary database or market-data failure
            # must not permanently terminate the worker.
            log.exception("Market monitoring cycle failed.")

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

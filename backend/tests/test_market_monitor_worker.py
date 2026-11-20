"""US-41: Tests for scheduled market monitoring."""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from app.services.market_monitor_worker import (
    get_monitoring_date,
    run_monitoring_cycle,
)

EASTERN = ZoneInfo("America/New_York")


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (
            datetime(2026, 11, 19, 17, 59, tzinfo=EASTERN),
            None,
        ),
        (
            datetime(2026, 11, 19, 18, 0, tzinfo=EASTERN),
            date(2026, 11, 19),
        ),
        (
            datetime(2026, 11, 21, 19, 0, tzinfo=EASTERN),
            None,
        ),
        (
            datetime(2026, 7, 17, 22, 0, tzinfo=timezone.utc),
            date(2026, 7, 17),
        ),
        (
            datetime(2026, 11, 19, 22, 0, tzinfo=timezone.utc),
            None,
        ),
    ],
)
def test_market_monitoring_schedule(now, expected):
    assert get_monitoring_date(now) == expected


def test_rejects_naive_datetime():
    with pytest.raises(ValueError):
        get_monitoring_date(datetime(2026, 11, 19, 18, 0))


def test_worker_executes_verified_scan():
    calls = []

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    def fake_scanner(db, session_date):
        calls.append((db, session_date))
        return 2

    now = datetime(2026, 11, 19, 19, 0, tzinfo=EASTERN)

    count = run_monitoring_cycle(
        now,
        session_factory=FakeSession,
        scanner=fake_scanner,
    )

    assert count == 2
    assert len(calls) == 1
    assert calls[0][1] == date(2026, 11, 19)


def test_worker_skips_before_market_check_time():
    def unexpected_session():
        raise AssertionError("Database should not be opened.")

    now = datetime(2026, 11, 19, 12, 0, tzinfo=EASTERN)

    count = run_monitoring_cycle(
        now,
        session_factory=unexpected_session,
    )

    assert count == 0

"""US-41: Market-change monitoring integration tests."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.market_alert import MarketAlert
from app.models.notification_event import NotificationEvent
from app.models.user import User
from app.services.market_alert_monitor import (
    scan_market_alerts,
    threshold_reached,
    valid_price,
)
from app.services.market_alert_runner import run_verified_market_scan

TRADING_DATE = date(2026, 11, 18)


@pytest.fixture
def monitor_db():
    """Provide an isolated database with two test investors."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            MarketAlert.__table__,
            NotificationEvent.__table__,
        ],
    )

    try:
        with Session(engine) as db:
            users = [
                User(
                    name="Investor A",
                    email="monitor-a@example.com",
                    password_hash="unused-test-hash",
                ),
                User(
                    name="Investor B",
                    email="monitor-b@example.com",
                    password_hash="unused-test-hash",
                ),
            ]
            db.add_all(users)
            db.commit()

            yield db, users[0].id, users[1].id
    finally:
        engine.dispose()


def add_alert(
    db,
    user_id,
    ticker="LMT",
    threshold="5",
    direction="increase",
    active=True,
):
    """Create and save a test market alert."""
    alert = MarketAlert(
        user_id=user_id,
        ticker=ticker,
        threshold_percent=Decimal(threshold),
        direction=direction,
        is_active=active,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def saved_notifications(db):
    return db.scalars(select(NotificationEvent).order_by(NotificationEvent.id)).all()


def quote(current, previous=100):
    return {
        "current_price": current,
        "previous_close": previous,
    }


@pytest.mark.parametrize(
    ("direction", "change", "expected"),
    [
        ("increase", "5", True),
        ("increase", "4.99", False),
        ("increase", "-6", False),
        ("decrease", "-5", True),
        ("decrease", "-4.99", False),
        ("decrease", "6", False),
        ("either", "5", True),
        ("either", "-5", True),
        ("either", "4.99", False),
        ("invalid", "6", False),
    ],
)
def test_threshold_directions(direction, change, expected):
    assert (
        threshold_reached(
            Decimal(change),
            Decimal("5"),
            direction,
        )
        is expected
    )


def test_create_notification_for_significant_increase(monitor_db):
    db, user_a, _ = monitor_db
    alert = add_alert(db, user_a)

    count = scan_market_alerts(
        db,
        TRADING_DATE,
        price_loader=lambda ticker: quote(106),
    )

    assert count == 1

    notifications = saved_notifications(db)
    assert len(notifications) == 1

    notification = notifications[0]
    assert notification.alert_id == alert.id
    assert notification.user_id == user_a
    assert notification.ticker == "LMT"
    assert notification.observed_change_percent == Decimal("6")
    assert notification.observed_price == Decimal("106")
    assert notification.reference_price == Decimal("100")
    assert notification.threshold_percent == Decimal("5")
    assert notification.is_read is False
    assert TRADING_DATE.isoformat() in notification.deduplication_key


def test_significant_decrease_creates_notification(monitor_db):
    db, user_a, _ = monitor_db
    add_alert(db, user_a, direction="decrease")

    count = scan_market_alerts(
        db,
        TRADING_DATE,
        price_loader=lambda ticker: quote(94),
    )

    assert count == 1
    assert saved_notifications(db)[0].observed_change_percent == Decimal("-6")


def test_below_threshold_does_not_trigger(monitor_db):
    db, user_a, _ = monitor_db
    add_alert(db, user_a, threshold="5")

    count = scan_market_alerts(
        db,
        TRADING_DATE,
        price_loader=lambda ticker: quote(103),
    )

    assert count == 0
    assert saved_notifications(db) == []


def test_inactive_alert_does_not_trigger(monitor_db):
    db, user_a, _ = monitor_db
    add_alert(db, user_a, active=False)

    calls = []

    def load_price(ticker):
        calls.append(ticker)
        return quote(110)

    count = scan_market_alerts(db, TRADING_DATE, price_loader=load_price)

    assert count == 0
    assert calls == []
    assert saved_notifications(db) == []


@pytest.mark.parametrize(
    "bad_quote",
    [
        quote(None),
        quote(0),
        quote(-10),
        quote("nan"),
        quote("inf"),
        quote(106, None),
        quote(106, 0),
        quote(106, -100),
        quote("invalid"),
    ],
)
def test_invalid_market_data_is_skipped(monitor_db, bad_quote):
    db, user_a, _ = monitor_db
    add_alert(db, user_a)

    count = scan_market_alerts(
        db,
        TRADING_DATE,
        price_loader=lambda ticker: bad_quote,
    )

    assert count == 0
    assert saved_notifications(db) == []


def test_market_data_provider_failure_is_handled(monitor_db):
    db, user_a, _ = monitor_db
    add_alert(db, user_a)

    def failing_loader(ticker):
        raise RuntimeError("Simulated market data outage")

    count = scan_market_alerts(
        db,
        TRADING_DATE,
        price_loader=failing_loader,
    )

    assert count == 0
    assert saved_notifications(db) == []


def test_same_alert_does_not_create_duplicate_notification(monitor_db):
    db, user_a, _ = monitor_db
    add_alert(db, user_a)

    def load_price(ticker):
        return quote(106)

    first = scan_market_alerts(db, TRADING_DATE, price_loader=load_price)
    second = scan_market_alerts(db, TRADING_DATE, price_loader=load_price)

    assert first == 1
    assert second == 0
    assert len(saved_notifications(db)) == 1


def test_separate_trading_dates_can_create_notifications(monitor_db):
    db, user_a, _ = monitor_db
    add_alert(db, user_a)

    first = scan_market_alerts(
        db,
        date(2026, 11, 17),
        price_loader=lambda ticker: quote(106),
    )
    second = scan_market_alerts(
        db,
        date(2026, 11, 18),
        price_loader=lambda ticker: quote(106),
    )

    assert first == 1
    assert second == 1
    assert len(saved_notifications(db)) == 2


def test_multiple_investors_receive_separate_notifications(monitor_db):
    db, user_a, user_b = monitor_db

    add_alert(db, user_a, ticker="LMT")
    add_alert(db, user_b, ticker="LMT")

    calls = []

    def load_price(ticker):
        calls.append(ticker)
        return quote(107)

    count = scan_market_alerts(
        db,
        TRADING_DATE,
        price_loader=load_price,
    )

    notifications = saved_notifications(db)

    assert count == 2
    assert len(notifications) == 2
    assert {item.user_id for item in notifications} == {
        user_a,
        user_b,
    }

    # The same ticker should only be fetched once per scan.
    assert calls == ["LMT"]


@pytest.mark.parametrize("value", [None, 0, -1, "nan", "inf", "bad"])
def test_valid_price_rejects_unusable_values(value):
    assert valid_price(value) is None


def test_verified_scan_creates_notification(monitor_db):
    db, user_a, _ = monitor_db
    add_alert(db, user_a, ticker="LMT", threshold="5")

    def history_loader(ticker, period):
        assert ticker == "LMT"
        assert period == "1M"
        return {
            "data": [
                {"date": "2026-11-17", "close": 100},
                {"date": "2026-11-18", "close": 106},
            ]
        }

    count = run_verified_market_scan(
        db,
        TRADING_DATE,
        history_loader=history_loader,
    )

    assert count == 1

    notifications = saved_notifications(db)
    assert len(notifications) == 1
    assert notifications[0].observed_price == Decimal("106")
    assert notifications[0].reference_price == Decimal("100")
    assert notifications[0].observed_change_percent == Decimal("6")


def test_verified_scan_rejects_stale_session(monitor_db):
    db, user_a, _ = monitor_db
    add_alert(db, user_a, ticker="LMT", threshold="5")

    def stale_history(ticker, period):
        return {
            "data": [
                {"date": "2026-11-16", "close": 100},
                {"date": "2026-11-17", "close": 110},
            ]
        }

    count = run_verified_market_scan(
        db,
        TRADING_DATE,
        history_loader=stale_history,
    )

    assert count == 0
    assert saved_notifications(db) == []


def test_verified_scan_prevents_duplicate_notifications(monitor_db):
    db, user_a, _ = monitor_db
    add_alert(db, user_a, ticker="LMT", threshold="5")

    def history_loader(ticker, period):
        return {
            "data": [
                {"date": "2026-11-17", "close": 100},
                {"date": "2026-11-18", "close": 108},
            ]
        }

    first = run_verified_market_scan(
        db,
        TRADING_DATE,
        history_loader=history_loader,
    )

    second = run_verified_market_scan(
        db,
        TRADING_DATE,
        history_loader=history_loader,
    )

    assert first == 1
    assert second == 0
    assert len(saved_notifications(db)) == 1

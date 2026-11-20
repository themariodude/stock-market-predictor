"""US-41: Tests for verified trading-session closing prices."""

from datetime import date
from decimal import Decimal

import pytest

from app.services.market_session_prices import get_verified_close_quote

SESSION_DATE = date(2026, 11, 18)


def fake_history(rows):
    def loader(ticker, period):
        assert ticker == "LMT"
        assert period == "1M"
        return {"data": rows}

    return loader


def test_valid_trading_session_returns_closing_prices():
    rows = [
        {"date": "2026-11-17", "close": 100},
        {"date": "2026-11-18", "close": 106},
    ]

    result = get_verified_close_quote(
        "LMT",
        SESSION_DATE,
        history_loader=fake_history(rows),
    )

    assert result == {
        "current_price": Decimal("106"),
        "previous_close": Decimal("100"),
    }


@pytest.mark.parametrize(
    "latest_date",
    ["2026-11-17", "2026-11-19"],
)
def test_rejects_wrong_trading_session(latest_date):
    rows = [
        {"date": "2026-11-16", "close": 100},
        {"date": latest_date, "close": 106},
    ]

    result = get_verified_close_quote(
        "LMT",
        SESSION_DATE,
        history_loader=fake_history(rows),
    )

    assert result is None


@pytest.mark.parametrize(
    ("previous_price", "latest_price"),
    [
        (100, None),
        (100, "NaN"),
        (100, -1),
        (0, 106),
    ],
)
def test_rejects_invalid_closing_prices(
    previous_price,
    latest_price,
):
    rows = [
        {"date": "2026-11-17", "close": previous_price},
        {"date": "2026-11-18", "close": latest_price},
    ]

    result = get_verified_close_quote(
        "LMT",
        SESSION_DATE,
        history_loader=fake_history(rows),
    )

    assert result is None


def test_rejects_insufficient_history():
    rows = [{"date": "2026-11-18", "close": 106}]

    result = get_verified_close_quote(
        "LMT",
        SESSION_DATE,
        history_loader=fake_history(rows),
    )

    assert result is None


def test_accepts_gap_between_trading_days():
    """A Monday session can use the preceding Friday's close."""
    rows = [
        {"date": "2026-11-13", "close": 100},
        {"date": "2026-11-16", "close": 105},
    ]

    result = get_verified_close_quote(
        "LMT",
        date(2026, 11, 16),
        history_loader=fake_history(rows),
    )

    assert result is not None
    assert result["previous_close"] == Decimal("100")
    assert result["current_price"] == Decimal("105")


def test_rejects_out_of_order_session_dates():
    rows = [
        {"date": "2026-11-18", "close": 100},
        {"date": "2026-11-18", "close": 106},
    ]

    result = get_verified_close_quote(
        "LMT",
        SESSION_DATE,
        history_loader=fake_history(rows),
    )

    assert result is None

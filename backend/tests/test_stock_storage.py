from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import StockPrice
from app.services.stock_storage import (
    get_stock_prices,
    store_stock_prices,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


def test_store_stock_prices_creates_stock_and_prices(db_session):
    records = [
        {
            "date": date(2026, 9, 15),
            "open": 475.00,
            "high": 486.00,
            "low": 474.00,
            "close": 485.50,
            "volume": 1234567,
        },
        {
            "date": date(2026, 9, 16),
            "open": 485.50,
            "high": 490.00,
            "low": 482.00,
            "close": 488.75,
            "volume": 1350000,
        },
    ]

    stock = store_stock_prices(
        db_session,
        ticker="LMT",
        company_name="Lockheed Martin",
        records=records,
    )

    assert stock.ticker == "LMT"
    assert stock.company_name == "Lockheed Martin"

    prices = db_session.query(StockPrice).all()

    assert len(prices) == 2
    assert prices[0].close == 485.50


def test_store_stock_prices_does_not_duplicate_same_date(db_session):
    first_record = [
        {
            "date": date(2026, 9, 15),
            "open": 475.00,
            "high": 486.00,
            "low": 474.00,
            "close": 485.50,
            "volume": 1234567,
        }
    ]

    updated_record = [
        {
            "date": date(2026, 9, 15),
            "open": 475.00,
            "high": 487.00,
            "low": 474.00,
            "close": 486.00,
            "volume": 1300000,
        }
    ]

    store_stock_prices(
        db_session,
        "LMT",
        "Lockheed Martin",
        first_record,
    )

    store_stock_prices(
        db_session,
        "LMT",
        "Lockheed Martin",
        updated_record,
    )

    prices = db_session.query(StockPrice).all()

    assert len(prices) == 1
    assert prices[0].close == 486.00
    assert prices[0].volume == 1300000


def test_get_stock_prices_returns_chronological_records(db_session):
    records = [
        {
            "date": date(2026, 9, 16),
            "open": 485.50,
            "high": 490.00,
            "low": 482.00,
            "close": 488.75,
            "volume": 1350000,
        },
        {
            "date": date(2026, 9, 15),
            "open": 475.00,
            "high": 486.00,
            "low": 474.00,
            "close": 485.50,
            "volume": 1234567,
        },
    ]

    store_stock_prices(
        db_session,
        "LMT",
        "Lockheed Martin",
        records,
    )

    prices = get_stock_prices(db_session, "lmt")

    assert len(prices) == 2
    assert prices[0].date == date(2026, 9, 15)
    assert prices[1].date == date(2026, 9, 16)


def test_get_stock_prices_unknown_ticker_returns_empty(db_session):
    assert get_stock_prices(db_session, "UNKNOWN") == []

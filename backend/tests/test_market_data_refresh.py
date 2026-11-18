import asyncio
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import Stock, StockPrice
from app.services import market_data_refresh


@pytest.fixture
def refresh_session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


def test_refresh_market_data_fetches_and_stores_each_supported_stock(
    monkeypatch, refresh_session_factory
):
    fetched = []
    monkeypatch.setattr(market_data_refresh, "SessionLocal", refresh_session_factory)

    def fake_history(ticker, time_range):
        fetched.append((ticker, time_range))
        return {
            "count": 1,
            "data": [
                {
                    "date": date(2026, 11, 16),
                    "open": 10,
                    "high": 12,
                    "low": 9,
                    "close": 11,
                    "volume": 100,
                }
            ],
        }

    monkeypatch.setattr(market_data_refresh, "get_historical_stock_data", fake_history)

    market_data_refresh.refresh_market_data()

    assert fetched == [(ticker, "1Y") for ticker in market_data_refresh.SUPPORTED_STOCKS]
    with Session(refresh_session_factory.kw["bind"]) as session:
        stocks = session.scalars(select(Stock)).all()
        prices = session.scalars(select(StockPrice)).all()
    assert {stock.ticker for stock in stocks} == set(market_data_refresh.SUPPORTED_STOCKS)
    assert len(prices) == len(market_data_refresh.SUPPORTED_STOCKS)


def test_refresh_continues_after_a_ticker_fails(monkeypatch, refresh_session_factory):
    fetched = []
    monkeypatch.setattr(market_data_refresh, "SessionLocal", refresh_session_factory)

    def fake_history(ticker, time_range):
        fetched.append(ticker)
        if ticker == "LMT":
            raise market_data_refresh.HistoricalStockDataError("provider unavailable")
        return {"count": 0, "data": []}

    monkeypatch.setattr(market_data_refresh, "get_historical_stock_data", fake_history)

    market_data_refresh.refresh_market_data()

    assert fetched == list(market_data_refresh.SUPPORTED_STOCKS)


def test_refresh_interval_defaults_to_one_day(monkeypatch):
    monkeypatch.delenv("MARKET_DATA_REFRESH_INTERVAL_SECONDS", raising=False)
    assert market_data_refresh.get_refresh_interval_seconds() == 86400


@pytest.mark.parametrize("value", ["0", "-10", "abc"])
def test_refresh_interval_rejects_invalid_values(monkeypatch, value):
    monkeypatch.setenv("MARKET_DATA_REFRESH_INTERVAL_SECONDS", value)
    with pytest.raises(ValueError, match="positive integer"):
        market_data_refresh.get_refresh_interval_seconds()


def test_refresh_loop_runs_immediately_then_waits(monkeypatch):
    refreshed = []

    def stop_after_first_wait(seconds):
        assert seconds == 60
        raise RuntimeError("stop test loop")

    monkeypatch.setattr(market_data_refresh, "refresh_market_data", lambda: refreshed.append(1))
    monkeypatch.setattr(asyncio, "sleep", stop_after_first_wait)

    with pytest.raises(RuntimeError, match="stop test loop"):
        asyncio.run(market_data_refresh.run_market_data_refresh(60))
    assert refreshed == [1]

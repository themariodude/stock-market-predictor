from datetime import date, datetime
from typing import Any, Iterable, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Stock, StockPrice


def _as_date(value: Any) -> date:
    """Convert supported date-like values to a Python date."""
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if hasattr(value, "date"):
        return value.date()

    raise TypeError("Stock price date must be date-like.")


def store_stock_prices(
    session: Session,
    ticker: str,
    company_name: str,
    records: Iterable[Mapping[str, Any]],
) -> Stock:
    """Store processed OHLCV records for one stock."""
    symbol = ticker.strip().upper()

    stock = session.scalar(select(Stock).where(Stock.ticker == symbol))

    if stock is None:
        stock = Stock(
            ticker=symbol,
            company_name=company_name,
        )
        session.add(stock)
        session.flush()

    try:
        for record in records:
            price_date = _as_date(record["date"])

            price = session.scalar(
                select(StockPrice).where(
                    StockPrice.stock_id == stock.id,
                    StockPrice.date == price_date,
                )
            )

            if price is None:
                price = StockPrice(
                    stock_id=stock.id,
                    date=price_date,
                    open=float(record["open"]),
                    high=float(record["high"]),
                    low=float(record["low"]),
                    close=float(record["close"]),
                    volume=int(record["volume"]),
                )
                session.add(price)
            else:
                price.open = float(record["open"])
                price.high = float(record["high"])
                price.low = float(record["low"])
                price.close = float(record["close"])
                price.volume = int(record["volume"])

        session.commit()
        session.refresh(stock)
        return stock

    except Exception:
        session.rollback()
        raise


def get_stock_prices(
    session: Session,
    ticker: str,
) -> list[StockPrice]:
    """Retrieve stored prices for a ticker in chronological order."""
    symbol = ticker.strip().upper()

    statement = (
        select(StockPrice)
        .join(Stock)
        .where(Stock.ticker == symbol)
        .order_by(StockPrice.date)
    )

    return list(session.scalars(statement).all())

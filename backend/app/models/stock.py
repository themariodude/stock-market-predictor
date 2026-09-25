from datetime import date

from sqlalchemy import (
    BigInteger,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    ticker: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        index=True,
        nullable=False,
    )

    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    prices: Mapped[list["StockPrice"]] = relationship(
        back_populates="stock",
        cascade="all, delete-orphan",
    )


class StockPrice(Base):
    __tablename__ = "stock_prices"

    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "date",
            name="uq_stock_price_stock_date",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id"),
        nullable=False,
        index=True,
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)

    volume: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    stock: Mapped[Stock] = relationship(
        back_populates="prices",
    )

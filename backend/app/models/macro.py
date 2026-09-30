from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MacroObservation(Base):
    __tablename__ = "macro_observations"

    __table_args__ = (
        UniqueConstraint(
            "series_id",
            "observation_date",
            "available_date",
            name="uq_macro_obs_series_date_available",
        ),
        CheckConstraint(
            "available_date >= observation_date",
            name="ck_macro_obs_available_after_observation",
        ),
        Index("ix_macro_obs_series_available", "series_id", "available_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[str] = mapped_column(String(50), nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    available_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_value: Mapped[str] = mapped_column(String(32), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

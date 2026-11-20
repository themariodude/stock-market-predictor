from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MarketAlert(Base):
    """Investor-defined stock market change alert."""

    __tablename__ = "market_alerts"

    __table_args__ = (
        CheckConstraint(
            "threshold_percent > 0 AND threshold_percent <= 100",
            name="ck_market_alerts_threshold",
        ),
        CheckConstraint(
            "direction IN ('increase', 'decrease', 'either')",
            name="ck_market_alerts_direction",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ticker: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )

    threshold_percent: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
    )

    direction: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    user_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    ticker: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    condition: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

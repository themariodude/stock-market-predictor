from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """Registered investor account stored in PostgreSQL."""

    __tablename__ = "users"
    # Unique ID
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    # Investor's Display Name
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    # Unique Email
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    # Securely hashed password
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    # Timestamp recording when account was created
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

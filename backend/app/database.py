import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""


DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None

SessionLocal = (
    sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    if engine is not None
    else None
)


def get_session() -> Session:
    """Create a database session using the configured database."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured.")

    return SessionLocal()

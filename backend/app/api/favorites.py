
"""API endpoints for managing favorite stocks."""

from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.favorite import Favorite

router = APIRouter(
    prefix="/favorites",
    tags=["favorites"],
)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session for a request."""
    db = get_session()

    try:
        yield db
    finally:
        db.close()


def get_user_email() -> str:
    """
    Placeholder for the existing authentication dependency.

    Replace this with verified user identity from your
    project's authentication system before enabling
    the favorites endpoints.
    """
    raise HTTPException(
        status_code=501,
        detail="Favorites authentication is not connected yet.",
    )


@router.get("")
def list_favorites(
    db: Session = Depends(get_db),
    user_email: str = Depends(get_user_email),
) -> list[dict]:
    """Return favorite stocks belonging to the logged-in user."""

    favorites = db.scalars(
        select(Favorite)
        .where(Favorite.user_email == user_email)
        .order_by(Favorite.ticker)
    ).all()

    return [
        {"ticker": favorite.ticker}
        for favorite in favorites
    ]

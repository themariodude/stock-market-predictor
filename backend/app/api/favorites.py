from collections.abc import Generator

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import _investor_from_authorization
from app.database import get_session
from app.models.favorite import Favorite
from app.services.ticker_validation import validate_ticker

router = APIRouter(
    prefix="/favorites",
    tags=["favorites"],
)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session for each request."""
    db = get_session()

    try:
        yield db
    finally:
        db.close()


def get_current_user_email(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> str:
    """Return the authenticated investor's email."""
    investor = _investor_from_authorization(authorization, db)
    return investor.email


@router.get("")
def list_favorites(
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
) -> list[dict]:
    """Return all favorite stocks for the logged-in investor."""

    favorites = db.scalars(
        select(Favorite)
        .where(Favorite.user_email == user_email)
        .order_by(Favorite.ticker)
    ).all()

    return [{"ticker": favorite.ticker} for favorite in favorites]


@router.post("/{ticker}", status_code=status.HTTP_201_CREATED)
def add_favorite(
    ticker: str,
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
) -> dict:
    """Add a stock to the logged-in investor's favorites."""

    ticker = validate_ticker(ticker)

    existing = db.scalar(
        select(Favorite).where(
            Favorite.user_email == user_email,
            Favorite.ticker == ticker,
        )
    )

    if existing:
        return {"ticker": existing.ticker}

    favorite = Favorite(
        user_email=user_email,
        ticker=ticker,
    )

    db.add(favorite)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Stock is already in favorites.",
        )

    return {"ticker": favorite.ticker}


@router.delete("/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    ticker: str,
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
) -> None:
    """Remove a stock from the logged-in investor's favorites."""

    ticker = validate_ticker(ticker)

    favorite = db.scalar(
        select(Favorite).where(
            Favorite.user_email == user_email,
            Favorite.ticker == ticker,
        )
    )

    if favorite is None:
        raise HTTPException(
            status_code=404,
            detail="Stock is not in favorites.",
        )

    db.delete(favorite)
    db.commit()

"""US-41: Authenticated market-change alert management."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.favorites import get_current_user_email, get_db
from app.models.market_alert import MarketAlert
from app.models.user import User
from app.services.ticker_validation import validate_ticker

router = APIRouter(prefix="/alerts", tags=["alerts"])

AlertDirection = Literal["increase", "decrease", "either"]


class AlertCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    threshold_percent: Decimal = Field(gt=0, le=100)
    direction: AlertDirection


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    threshold_percent: Decimal
    direction: AlertDirection
    is_active: bool
    created_at: datetime
    updated_at: datetime


def get_current_user_id(
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
) -> int:
    """Resolve the authenticated investor's database ID."""
    user = db.scalar(select(User).where(User.email == user_email))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated investor not found.",
        )

    return user.id


@router.post(
    "",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_alert(
    payload: AlertCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> MarketAlert:
    """Create a market-change alert for the investor."""
    ticker = validate_ticker(payload.ticker)

    alert = MarketAlert(
        user_id=user_id,
        ticker=ticker,
        threshold_percent=payload.threshold_percent,
        direction=payload.direction,
        is_active=True,
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return alert


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[MarketAlert]:
    """Return alerts owned by the authenticated investor."""
    return list(
        db.scalars(
            select(MarketAlert)
            .where(MarketAlert.user_id == user_id)
            .order_by(MarketAlert.created_at.desc())
        ).all()
    )

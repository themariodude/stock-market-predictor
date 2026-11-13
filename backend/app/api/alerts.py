
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.favorites import get_current_user_email, get_db
from app.models.alert import Alert
from app.services.ticker_validation import (
    is_supported_ticker,
    normalize_ticker,
)


router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
)

class AlertCreate(BaseModel):
    ticker: str
    condition: Literal["above", "below"]
    threshold: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        ticker = normalize_ticker(value)

        if not is_supported_ticker(ticker):
            raise ValueError("Unsupported stock ticker.")

        return ticker


class AlertResponse(BaseModel):
    id: int
    ticker: str
    condition: str
    threshold: float
    created_at: datetime

    model_config = {"from_attributes": True}

@router.post(
    "",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_alert(
    payload: AlertCreate,
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    alert = Alert(
        user_email=user_email,
        ticker=payload.ticker,
        condition=payload.condition,
        threshold=payload.threshold,
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return alert

@router.get(
    "",
    response_model=list[AlertResponse],
)
def list_alerts(
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    alerts = db.scalars(
        select(Alert)
        .where(Alert.user_email == user_email)
        .order_by(
            Alert.created_at.desc(),
            Alert.id.desc(),
        )
    ).all()

    return alerts

@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    alert = db.scalar(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.user_email == user_email,
        )
    )

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )

    db.delete(alert)
    db.commit()

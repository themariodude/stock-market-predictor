"""US-41: Authenticated market notification history API."""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.favorites import get_db
from app.api.market_alerts import get_current_user_id
from app.models.notification_event import NotificationEvent

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_id: int | None
    ticker: str
    threshold_percent: Decimal
    observed_change_percent: Decimal
    observed_price: Decimal
    reference_price: Decimal
    triggered_at: datetime
    is_read: bool


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[NotificationEvent]:
    """List notifications belonging to the logged-in investor."""
    return list(
        db.scalars(
            select(NotificationEvent)
            .where(NotificationEvent.user_id == user_id)
            .order_by(
                NotificationEvent.triggered_at.desc(),
                NotificationEvent.id.desc(),
            )
        ).all()
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> NotificationEvent:
    """Mark an investor-owned notification as read."""
    notification = db.scalar(
        select(NotificationEvent).where(
            NotificationEvent.id == notification_id,
            NotificationEvent.user_id == user_id,
        )
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    notification.is_read = True

    db.commit()
    db.refresh(notification)

    return notification

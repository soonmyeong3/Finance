from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationOut
from app.services.life_event_detector import sync_notifications

router = APIRouter(prefix="/users/{user_id}/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(user_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )


@router.post("/detect", response_model=list[NotificationOut])
def detect_notifications(user_id: int, db: Session = Depends(get_db)):
    """Runs life-event detection over the user's card transactions and
    replaces their notification list with the result. Stands in for the
    periodic batch job a real deployment would run on a schedule."""
    return sync_notifications(db, user_id)

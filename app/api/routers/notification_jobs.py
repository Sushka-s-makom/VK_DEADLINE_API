from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import NotificationJob
from app.schemas.notification_job import NotificationJobRead

router = APIRouter(prefix="/notification-jobs", tags=["notification-jobs"])


@router.get("", response_model=list[NotificationJobRead])
def list_notification_jobs(db: Session = Depends(get_db)) -> list[NotificationJob]:
    return list(db.scalars(select(NotificationJob).order_by(NotificationJob.send_at, NotificationJob.id)).all())


@router.get("/{item_id}", response_model=NotificationJobRead)
def get_notification_job(item_id: int, db: Session = Depends(get_db)) -> NotificationJob:
    item = db.get(NotificationJob, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Notification job not found")
    return item

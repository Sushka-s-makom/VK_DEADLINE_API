from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import NotificationRule
from app.schemas.notification_rule import NotificationRuleCreate, NotificationRuleRead, NotificationRuleUpdate

router = APIRouter(prefix="/notification-rules", tags=["notification-rules"])


@router.post("", response_model=NotificationRuleRead, status_code=201)
def create_notification_rule(payload: NotificationRuleCreate, db: Session = Depends(get_db)) -> NotificationRule:
    item = NotificationRule(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[NotificationRuleRead])
def list_notification_rules(db: Session = Depends(get_db)) -> list[NotificationRule]:
    return list(db.scalars(select(NotificationRule).order_by(NotificationRule.send_before_minutes.desc())).all())


@router.patch("/{item_id}", response_model=NotificationRuleRead)
def update_notification_rule(item_id: int, payload: NotificationRuleUpdate, db: Session = Depends(get_db)) -> NotificationRule:
    item = db.get(NotificationRule, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Notification rule not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

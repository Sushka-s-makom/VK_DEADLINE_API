from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Deadline
from app.schemas.deadline import DeadlineCreate, DeadlineRead, DeadlineUpdate
from app.services.notification_job_service import create_jobs_for_deadline, recalculate_future_jobs_for_deadline

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


@router.post("", response_model=DeadlineRead, status_code=201)
def create_deadline(payload: DeadlineCreate, db: Session = Depends(get_db)) -> Deadline:
    item = Deadline(**payload.model_dump())
    db.add(item)
    try:
        db.flush()
        create_jobs_for_deadline(db, item)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Deadline already exists or related entity is missing") from exc
    db.refresh(item)
    return item


@router.get("", response_model=list[DeadlineRead])
def list_deadlines(db: Session = Depends(get_db)) -> list[Deadline]:
    return list(db.scalars(select(Deadline).order_by(Deadline.deadline_at)).all())


@router.get("/{item_id}", response_model=DeadlineRead)
def get_deadline(item_id: int, db: Session = Depends(get_db)) -> Deadline:
    item = db.get(Deadline, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return item


@router.patch("/{item_id}", response_model=DeadlineRead)
def update_deadline(item_id: int, payload: DeadlineUpdate, db: Session = Depends(get_db)) -> Deadline:
    item = db.get(Deadline, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Deadline not found")

    data = payload.model_dump(exclude_unset=True)
    deadline_changed = "deadline_at" in data
    for key, value in data.items():
        setattr(item, key, value)
    if deadline_changed:
        recalculate_future_jobs_for_deadline(db, item)
    db.commit()
    db.refresh(item)
    return item

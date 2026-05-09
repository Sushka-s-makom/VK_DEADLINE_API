from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import StudyGroup
from app.schemas.study_group import StudyGroupCreate, StudyGroupRead

router = APIRouter(prefix="/study-groups", tags=["study-groups"])


@router.post("", response_model=StudyGroupRead, status_code=201)
def create_study_group(payload: StudyGroupCreate, db: Session = Depends(get_db)) -> StudyGroup:
    item = StudyGroup(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Study group already exists") from exc
    db.refresh(item)
    return item


@router.get("", response_model=list[StudyGroupRead])
def list_study_groups(db: Session = Depends(get_db)) -> list[StudyGroup]:
    return list(db.scalars(select(StudyGroup).order_by(StudyGroup.id)).all())


@router.get("/{item_id}", response_model=StudyGroupRead)
def get_study_group(item_id: int, db: Session = Depends(get_db)) -> StudyGroup:
    item = db.get(StudyGroup, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Study group not found")
    return item

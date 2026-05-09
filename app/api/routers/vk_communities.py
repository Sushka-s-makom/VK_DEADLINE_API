from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import VKCommunity
from app.schemas.vk_community import VKCommunityCreate, VKCommunityRead

router = APIRouter(prefix="/vk-communities", tags=["vk-communities"])


@router.post("", response_model=VKCommunityRead, status_code=201)
def create_vk_community(payload: VKCommunityCreate, db: Session = Depends(get_db)) -> VKCommunity:
    item = VKCommunity(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="VK community already exists") from exc
    db.refresh(item)
    return item


@router.get("", response_model=list[VKCommunityRead])
def list_vk_communities(db: Session = Depends(get_db)) -> list[VKCommunity]:
    return list(db.scalars(select(VKCommunity).order_by(VKCommunity.id)).all())


@router.get("/{item_id}", response_model=VKCommunityRead)
def get_vk_community(item_id: int, db: Session = Depends(get_db)) -> VKCommunity:
    item = db.get(VKCommunity, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="VK community not found")
    return item

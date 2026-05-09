from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import VKChat
from app.schemas.vk_chat import VKChatCreate, VKChatRead

router = APIRouter(prefix="/vk-chats", tags=["vk-chats"])


@router.post("", response_model=VKChatRead, status_code=201)
def create_vk_chat(payload: VKChatCreate, db: Session = Depends(get_db)) -> VKChat:
    item = VKChat(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="VK chat already exists or related entity is missing") from exc
    db.refresh(item)
    return item


@router.get("", response_model=list[VKChatRead])
def list_vk_chats(db: Session = Depends(get_db)) -> list[VKChat]:
    return list(db.scalars(select(VKChat).order_by(VKChat.id)).all())


@router.get("/{item_id}", response_model=VKChatRead)
def get_vk_chat(item_id: int, db: Session = Depends(get_db)) -> VKChat:
    item = db.get(VKChat, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="VK chat not found")
    return item

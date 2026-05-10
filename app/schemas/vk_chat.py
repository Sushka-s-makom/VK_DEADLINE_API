from pydantic import BaseModel

from app.schemas.common import Timestamped


class VKChatCreate(BaseModel):
    study_group_id: int
    community_id: int
    peer_id: int
    title: str | None = None
    is_active: bool = True


class VKChatRead(Timestamped):
    id: int
    study_group_id: int
    community_id: int
    peer_id: int
    title: str | None
    is_active: bool

from pydantic import BaseModel

from app.schemas.common import Timestamped


class StudyGroupCreate(BaseModel):
    title: str
    subject: str | None = None
    external_group_id: str | None = None
    is_active: bool = True


class StudyGroupRead(Timestamped):
    id: int
    title: str
    subject: str | None
    external_group_id: str | None
    is_active: bool

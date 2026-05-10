from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import Timestamped


class DeadlineCreate(BaseModel):
    study_group_id: int
    external_deadline_id: str | None = None
    subject: str | None = None
    title: str
    description: str | None = None
    deadline_at: datetime
    source: str = "manual"


class DeadlineUpdate(BaseModel):
    external_deadline_id: str | None = None
    subject: str | None = None
    title: str | None = None
    description: str | None = None
    deadline_at: datetime | None = None
    source: str | None = None


class DeadlineRead(Timestamped):
    id: int
    study_group_id: int
    external_deadline_id: str | None
    subject: str | None
    title: str
    description: str | None
    deadline_at: datetime
    source: str

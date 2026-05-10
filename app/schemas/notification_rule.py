from pydantic import BaseModel, Field

from app.schemas.common import Timestamped


class NotificationRuleCreate(BaseModel):
    title: str
    send_before_minutes: int = Field(ge=0)
    schedule_type: str = "before_deadline"
    send_time_local: str | None = None
    send_window_start_local: str | None = None
    send_window_end_local: str | None = None
    text_template: str
    is_active: bool = True


class NotificationRuleUpdate(BaseModel):
    title: str | None = None
    send_before_minutes: int | None = Field(default=None, ge=0)
    schedule_type: str | None = None
    send_time_local: str | None = None
    send_window_start_local: str | None = None
    send_window_end_local: str | None = None
    text_template: str | None = None
    is_active: bool | None = None


class NotificationRuleRead(Timestamped):
    id: int
    title: str
    send_before_minutes: int
    schedule_type: str
    send_time_local: str | None
    send_window_start_local: str | None
    send_window_end_local: str | None
    text_template: str
    is_active: bool

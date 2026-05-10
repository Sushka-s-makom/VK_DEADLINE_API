from datetime import datetime

from app.schemas.common import Timestamped


class NotificationJobRead(Timestamped):
    id: int
    deadline_id: int
    vk_chat_id: int
    rule_id: int
    send_at: datetime
    status: str
    attempts: int
    last_error: str | None
    vk_message_id: int | None
    sent_at: datetime | None

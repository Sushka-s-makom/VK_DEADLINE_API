from __future__ import annotations

from datetime import datetime

from vk_deadline_bot.app.domain.models import Deadline
from vk_deadline_bot.app.domain.timeutils import to_utc


def format_deadline_reminder(deadline: Deadline, now: datetime) -> str:
    """Формирует текст напоминания о дедлайне.

    В MVP это простой текст. Позже можно вынести шаблоны в БД/конфиг.
    """
    due_at = to_utc(deadline.due_at)
    now = to_utc(now)
    delta = due_at - now

    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)

    if delta.total_seconds() <= 0:
        time_left = "дедлайн уже наступил!"
    elif hours > 0:
        time_left = f"осталось примерно {hours} ч {minutes} мин"
    else:
        time_left = f"осталось примерно {minutes} мин"

    return (
        f"Напоминание о дедлайне:\n"
        f"• Задание: {deadline.title}\n"
        f"• Описание: {deadline.description or '—'}\n"
        f"• Дедлайн: {due_at.isoformat()}\n"
        f"• Статус: {time_left}"
    )


__all__ = ["format_deadline_reminder"]


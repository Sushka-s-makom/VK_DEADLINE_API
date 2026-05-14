from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, List


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """Приводит datetime к UTC (если без tz, принимает как локальное время)."""
    if dt.tzinfo is None:
        # В MVP можно считать, что локальное = UTC, позже можно доработать
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def build_remind_times(due_at: datetime, offsets: Iterable[timedelta]) -> List[datetime]:
    """Возвращает моменты напоминаний относительно дедлайна."""
    due_at_utc = to_utc(due_at)
    return [due_at_utc - offset for offset in offsets]


__all__ = ["now_utc", "to_utc", "build_remind_times"]


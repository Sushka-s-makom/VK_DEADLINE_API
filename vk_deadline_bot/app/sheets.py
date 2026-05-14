from __future__ import annotations

from typing import List

from vk_deadline_bot.app.config import AppConfig
from vk_deadline_bot.app.domain.models import Course, Deadline


async def fetch_deadlines_for_course(config: AppConfig, course: Course) -> List[Deadline]:
    """Чтение дедлайнов для курса из Google Sheets.

    Здесь только каркас: подключение к Google API и парсинг таблицы
    нужно реализовать отдельно.
    """
    # TODO: реализовать чтение реальных данных из Google Sheets.
    # Пока возвращаем пустой список, чтобы не ломать остальной код.
    return []


__all__ = ["fetch_deadlines_for_course"]


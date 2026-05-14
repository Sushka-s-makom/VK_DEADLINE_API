from __future__ import annotations

from datetime import timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from vk_deadline_bot.app.config import get_config
from vk_deadline_bot.app.domain.timeutils import now_utc
from vk_deadline_bot.app.sheets import fetch_deadlines_for_course
from vk_deadline_bot.app.storage.db import get_pool
from vk_deadline_bot.app.storage.repositories import CoursesRepository, DeadlinesRepository


_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def sync_deadlines_job() -> None:
    """Периодический джоб для синхронизации дедлайнов из Google Sheets."""
    config = get_config()
    courses_repo = CoursesRepository()
    deadlines_repo = DeadlinesRepository()

    courses = await courses_repo.list_all()
    for course in courses:
        if not course.sheet_id:
            continue
        deadlines = await fetch_deadlines_for_course(config, course)
        await deadlines_repo.upsert_deadlines_for_course(course, deadlines)


async def send_notifications_job() -> None:
    """Периодический джоб для отправки напоминаний.

    Здесь оставлен каркас: нужно реализовать выборку reminders + vk_groups
    и отправку сообщений через VkClient.
    """
    _ = get_pool()  # гарантируем, что пул инициализирован
    # TODO: реализовать выборку и отправку напоминаний
    _now = now_utc()
    # place for future logic
    return None


def setup_scheduler() -> AsyncIOScheduler:
    """Создаёт и конфигурирует шедулер с нужными джобами."""
    scheduler = get_scheduler()

    # Синк дедлайнов каждые 5 минут
    scheduler.add_job(sync_deadlines_job, "interval", minutes=5, id="sync_deadlines")

    # Отправка уведомлений каждую минуту
    scheduler.add_job(send_notifications_job, "interval", minutes=1, id="send_notifications")

    return scheduler


__all__ = ["get_scheduler", "setup_scheduler", "sync_deadlines_job", "send_notifications_job"]


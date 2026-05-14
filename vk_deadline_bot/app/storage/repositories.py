from __future__ import annotations

from typing import Iterable, List, Optional

from vk_deadline_bot.app.domain.models import Course, Deadline, Group
from vk_deadline_bot.app.storage.db import get_pool


class GroupsRepository:
    async def upsert_group(self, peer_id: int, course_id: int, title: Optional[str] = None) -> None:
        """Создаёт или обновляет связь peer_id -> course_id."""
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO vk_groups (peer_id, course_id, title)
                VALUES ($1, $2, $3)
                ON CONFLICT (peer_id) DO UPDATE
                SET course_id = EXCLUDED.course_id,
                    title     = COALESCE(EXCLUDED.title, vk_groups.title)
                """,
                peer_id,
                course_id,
                title,
            )

    async def get_group_by_peer_id(self, peer_id: int) -> Optional[Group]:
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, peer_id, course_id, title FROM vk_groups WHERE peer_id = $1",
                peer_id,
            )
        if row is None:
            return None
        return Group(
            id=row["id"],
            peer_id=row["peer_id"],
            course_id=row["course_id"],
            title=row["title"],
        )


class CoursesRepository:
    async def get_by_vk_code(self, vk_code: str) -> Optional[Course]:
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, subject_id, name, vk_code, sheet_id, sheet_range
                FROM courses
                WHERE vk_code = $1
                """,
                vk_code,
            )
        if row is None:
            return None
        return Course(
            id=row["id"],
            subject_id=row["subject_id"],
            name=row["name"],
            vk_code=row["vk_code"],
            sheet_id=row["sheet_id"],
            sheet_range=row["sheet_range"],
        )

    async def list_all(self) -> List[Course]:
        pool = get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, subject_id, name, vk_code, sheet_id, sheet_range FROM courses"
            )
        return [
            Course(
                id=row["id"],
                subject_id=row["subject_id"],
                name=row["name"],
                vk_code=row["vk_code"],
                sheet_id=row["sheet_id"],
                sheet_range=row["sheet_range"],
            )
            for row in rows
        ]


class DeadlinesRepository:
    async def upsert_deadlines_for_course(self, course: Course, deadlines: Iterable[Deadline]) -> None:
        """Простой вариант: удаляем старые и вставляем новые дедлайны для курса."""
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM deadlines WHERE course_id = $1", course.id)
                for d in deadlines:
                    await conn.execute(
                        """
                        INSERT INTO deadlines (course_id, title, description, due_at)
                        VALUES ($1, $2, $3, $4)
                        """,
                        course.id,
                        d.title,
                        d.description,
                        d.due_at,
                    )

    async def list_upcoming_deadlines(self, course_id: int):
        # Заглушка, можно реализовать фильтрацию по времени
        pool = get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, course_id, title, description, due_at
                FROM deadlines
                WHERE course_id = $1
                """,
                course_id,
            )
        return [
            Deadline(
                id=row["id"],
                course_id=row["course_id"],
                title=row["title"],
                description=row["description"],
                due_at=row["due_at"],
            )
            for row in rows
        ]


class SentNotificationsRepository:
    async def mark_sent(self, reminder_id: int, peer_id: int) -> None:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sent_notifications (reminder_id, peer_id)
                VALUES ($1, $2)
                ON CONFLICT (reminder_id, peer_id) DO NOTHING
                """,
                reminder_id,
                peer_id,
            )


__all__ = [
    "GroupsRepository",
    "CoursesRepository",
    "DeadlinesRepository",
    "SentNotificationsRepository",
]


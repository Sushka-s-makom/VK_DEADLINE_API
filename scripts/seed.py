from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import Deadline, NotificationRule, StudyGroup, VKChat, VKCommunity
from app.services.notification_job_service import create_jobs_for_deadline

TEXT_TEMPLATE = "ВАЖНО: дедлайн по предмету {subject}: {title}. Сдать до {deadline_at}. {description}"


def seed() -> None:
    with SessionLocal() as db:
        community = db.scalar(select(VKCommunity).where(VKCommunity.vk_group_id == 123456789))
        if community is None:
            community = VKCommunity(
                title="Demo online school",
                vk_group_id=123456789,
                token_env_name="VK_GROUP_TOKEN",
            )
            db.add(community)
            db.flush()

        groups_data = [
            ("Физика ЕГЭ 2026 | Группа А", "Физика", "physics-ege-2026-a", 2000000123),
            ("Математика ЕГЭ 2026 | Группа B", "Математика", "math-ege-2026-b", 2000000124),
            ("Информатика ЕГЭ 2026 | Группа C", "Информатика", "cs-ege-2026-c", 2000000125),
        ]
        groups: list[StudyGroup] = []
        for title, subject, external_id, peer_id in groups_data:
            group = db.scalar(select(StudyGroup).where(StudyGroup.external_group_id == external_id))
            if group is None:
                group = StudyGroup(title=title, subject=subject, external_group_id=external_id)
                db.add(group)
                db.flush()
            groups.append(group)

            chat = db.scalar(select(VKChat).where(VKChat.community_id == community.id, VKChat.peer_id == peer_id))
            if chat is None:
                db.add(VKChat(study_group_id=group.id, community_id=community.id, peer_id=peer_id, title=title))

        rules_data = [
            ("За 7 дней", 10080),
            ("За 1 день", 1440),
            ("За 3 часа", 180),
            ("За 1 час", 60),
        ]
        for title, minutes in rules_data:
            rule = db.scalar(select(NotificationRule).where(NotificationRule.send_before_minutes == minutes))
            if rule is None:
                db.add(NotificationRule(title=title, send_before_minutes=minutes, text_template=TEXT_TEMPLATE))
        db.flush()

        now = datetime.now(timezone.utc)
        deadlines_data = [
            (groups[0], "Домашнее задание по динамике", "Решить задачи 1-15", now + timedelta(days=8, hours=2)),
            (groups[0], "Пробник по механике", "Выполнить вариант полностью", now + timedelta(days=3, hours=5)),
            (groups[1], "Тригонометрия", "Сдать тест в LMS", now + timedelta(days=5)),
            (groups[1], "Производные", "Разобрать задания 7-12", now + timedelta(days=1, hours=4)),
            (groups[2], "Алгоритмы", "Решить задачи A-D", now + timedelta(hours=6)),
        ]
        for index, (group, title, description, deadline_at) in enumerate(deadlines_data, start=1):
            external_id = f"seed-{index}"
            deadline = db.scalar(
                select(Deadline).where(
                    Deadline.study_group_id == group.id,
                    Deadline.external_deadline_id == external_id,
                )
            )
            if deadline is None:
                deadline = Deadline(
                    study_group_id=group.id,
                    external_deadline_id=external_id,
                    subject=group.subject,
                    title=title,
                    description=description,
                    deadline_at=deadline_at,
                    source="manual",
                )
                db.add(deadline)
                db.flush()
                create_jobs_for_deadline(db, deadline)

        db.commit()


if __name__ == "__main__":
    seed()

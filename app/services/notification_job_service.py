import hashlib
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.db.models import Deadline, NotificationJob, NotificationJobStatus, NotificationRule, VKChat


def get_due_now() -> datetime:
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        return datetime.now().replace(tzinfo=None)
    return datetime.now(timezone.utc)


def parse_hhmm(value: str) -> time:
    hour, minute = [int(part) for part in value.split(":", 1)]
    return time(hour=hour, minute=minute)


def stable_window_offset_seconds(deadline_id: int, vk_chat_id: int, rule_id: int, window_seconds: int) -> int:
    key = f"{deadline_id}:{vk_chat_id}:{rule_id}".encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()
    return int(digest[:12], 16) % max(window_seconds, 1)


def calculate_send_at(deadline: Deadline, rule: NotificationRule, vk_chat: VKChat | None = None) -> datetime:
    if rule.schedule_type == "deadline_day_time" and rule.send_time_local:
        return datetime.combine(deadline.deadline_at.date(), parse_hhmm(rule.send_time_local))
    if (
        rule.schedule_type == "deadline_day_window"
        and rule.send_window_start_local
        and rule.send_window_end_local
        and vk_chat is not None
    ):
        start = datetime.combine(deadline.deadline_at.date(), parse_hhmm(rule.send_window_start_local))
        end = datetime.combine(deadline.deadline_at.date(), parse_hhmm(rule.send_window_end_local))
        if end <= start:
            end += timedelta(days=1)
        offset = stable_window_offset_seconds(deadline.id, vk_chat.id, rule.id, int((end - start).total_seconds()))
        return start + timedelta(seconds=offset)
    return deadline.deadline_at - timedelta(minutes=rule.send_before_minutes)


def create_jobs_for_deadline(db: Session, deadline: Deadline, skip_past_send_at: bool = False) -> int:
    rules = db.scalars(select(NotificationRule).where(NotificationRule.is_active.is_(True))).all()
    chats = db.scalars(
        select(VKChat).where(VKChat.study_group_id == deadline.study_group_id, VKChat.is_active.is_(True))
    ).all()

    created = 0
    for chat in chats:
        for rule in rules:
            send_at = calculate_send_at(deadline, rule, chat)
            if skip_past_send_at and send_at.replace(tzinfo=None) <= get_due_now().replace(tzinfo=None):
                continue
            existing = db.scalar(
                select(NotificationJob.id).where(
                    NotificationJob.deadline_id == deadline.id,
                    NotificationJob.vk_chat_id == chat.id,
                    NotificationJob.rule_id == rule.id,
                )
            )
            if existing is not None:
                continue
            db.add(
                NotificationJob(
                    deadline_id=deadline.id,
                    vk_chat_id=chat.id,
                    rule_id=rule.id,
                    send_at=send_at,
                    status=NotificationJobStatus.pending.value,
                )
            )
            created += 1
    return created


def recalculate_future_jobs_for_deadline(db: Session, deadline: Deadline) -> int:
    jobs = db.scalars(
        select(NotificationJob)
        .join(NotificationRule)
        .where(
            NotificationJob.deadline_id == deadline.id,
            NotificationJob.status.in_([NotificationJobStatus.pending.value, NotificationJobStatus.retry.value]),
        )
    ).all()
    for job in jobs:
        job.send_at = calculate_send_at(deadline, job.rule, job.vk_chat)
    return len(jobs)


def get_due_jobs(db: Session, limit: int = 100) -> list[NotificationJob]:
    now = get_due_now()
    return list(
        db.scalars(
            select(NotificationJob)
            .options(
                joinedload(NotificationJob.deadline),
                joinedload(NotificationJob.rule),
                joinedload(NotificationJob.vk_chat).joinedload(VKChat.community),
            )
            .where(
                NotificationJob.status.in_([NotificationJobStatus.pending.value, NotificationJobStatus.retry.value]),
                NotificationJob.send_at <= now,
            )
            .order_by(NotificationJob.send_at.asc())
            .limit(limit)
        ).all()
    )


def claim_due_jobs(db: Session, limit: int = 100) -> list[int]:
    jobs = get_due_jobs(db, limit=limit)
    job_ids: list[int] = []
    for job in jobs:
        job.status = NotificationJobStatus.processing.value
        job_ids.append(job.id)
    db.commit()
    return job_ids


def reset_stale_processing_jobs(db: Session, stale_after_minutes: int = 30) -> int:
    threshold = get_due_now() - timedelta(minutes=stale_after_minutes)
    jobs = db.scalars(
        select(NotificationJob).where(
            NotificationJob.status == NotificationJobStatus.processing.value,
            NotificationJob.updated_at <= threshold,
        )
    ).all()
    for job in jobs:
        job.status = NotificationJobStatus.retry.value
        job.last_error = "Reset stale processing job"
    db.commit()
    return len(jobs)

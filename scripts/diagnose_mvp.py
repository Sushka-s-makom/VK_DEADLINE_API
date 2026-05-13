from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select, func

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import Deadline, NotificationJob, NotificationRule, StudyGroup, VKChat, VKCommunity
from app.services.notification_job_service import get_due_now


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def main() -> int:
    load_dotenv(dotenv_path=Path(".env"))
    settings = get_settings()
    now = get_due_now()

    with SessionLocal() as db:
        print("VK Deadline MVP diagnostics")
        print("now:", now.strftime("%Y-%m-%d %H:%M:%S"))
        print("database_url:", settings.database_url)
        print("vk_token_loaded:", yes_no(bool(os.getenv("VK_GROUP_TOKEN"))))
        print()

        for model, title in [
            (VKCommunity, "vk_communities"),
            (StudyGroup, "study_groups"),
            (VKChat, "vk_chats"),
            (Deadline, "deadlines"),
            (NotificationRule, "notification_rules"),
            (NotificationJob, "notification_jobs"),
        ]:
            print(f"{title}:", db.scalar(select(func.count()).select_from(model)))

        print()
        print("job statuses:")
        rows = db.execute(
            select(NotificationJob.status, func.count()).group_by(NotificationJob.status).order_by(NotificationJob.status)
        ).all()
        for status, count in rows:
            print(f"  {status}: {count}")

        due_count = db.scalar(
            select(func.count())
            .select_from(NotificationJob)
            .where(
                NotificationJob.status.in_(["pending", "retry"]),
                NotificationJob.send_at <= now,
            )
        )
        stale_processing = db.scalar(
            select(func.count())
            .select_from(NotificationJob)
            .where(
                NotificationJob.status == "processing",
                NotificationJob.updated_at <= now - timedelta(minutes=30),
            )
        )
        print()
        print("due_jobs_now:", due_count)
        print("stale_processing_30m:", stale_processing)

        print()
        print("active rules:")
        for rule in db.scalars(select(NotificationRule).where(NotificationRule.is_active.is_(True)).order_by(NotificationRule.id)):
            print(
                f"  id={rule.id} title={rule.title!r} type={rule.schedule_type} "
                f"time={rule.send_time_local} window={rule.send_window_start_local}-{rule.send_window_end_local}"
            )

        print()
        print("next 10 jobs:")
        jobs = db.scalars(
            select(NotificationJob)
            .where(NotificationJob.status.in_(["pending", "retry"]))
            .order_by(NotificationJob.send_at)
            .limit(10)
        ).all()
        for job in jobs:
            print(
                f"  job_id={job.id} send_at={job.send_at} status={job.status} "
                f"deadline_id={job.deadline_id} chat_id={job.vk_chat_id} attempts={job.attempts}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

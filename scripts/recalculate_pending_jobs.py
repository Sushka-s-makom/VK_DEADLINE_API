from __future__ import annotations

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import NotificationJob, NotificationJobStatus
from app.services.notification_job_service import calculate_send_at, get_due_now


def main() -> int:
    now = get_due_now()
    updated = 0
    deleted_past = 0
    with SessionLocal() as db:
        jobs = db.scalars(
            select(NotificationJob).where(
                NotificationJob.status.in_([NotificationJobStatus.pending.value, NotificationJobStatus.retry.value])
            )
        ).all()
        for job in jobs:
            send_at = calculate_send_at(job.deadline, job.rule, job.vk_chat)
            if send_at.replace(tzinfo=None) <= now.replace(tzinfo=None):
                db.delete(job)
                deleted_past += 1
                continue
            job.send_at = send_at
            updated += 1
        db.commit()

    print("updated:", updated)
    print("deleted_past:", deleted_past)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

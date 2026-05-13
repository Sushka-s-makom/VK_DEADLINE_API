from __future__ import annotations

from datetime import datetime, timezone
import argparse

from sqlalchemy.orm import joinedload

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import NotificationJob, NotificationJobStatus, VKChat
from app.services.notification_job_service import claim_due_jobs, get_due_jobs, reset_stale_processing_jobs
from app.services.vk_sender import VKSender


def send_due_notifications(limit: int = 100, dry_run: bool = False, reset_stale: bool = True) -> int:
    settings = get_settings()
    sent_or_updated = 0

    with SessionLocal() as db:
        if dry_run:
            due_jobs = get_due_jobs(db, limit=limit)
            for job in due_jobs:
                print(f"dry_run job_id={job.id} send_at={job.send_at} peer_id={job.vk_chat.peer_id}")
            return len(due_jobs)
        if reset_stale:
            reset_stale_processing_jobs(db)
        job_ids = claim_due_jobs(db, limit=limit)

    sender = VKSender()
    for job_id in job_ids:
        with SessionLocal() as db:
            job = (
                db.query(NotificationJob)
                .options(
                    joinedload(NotificationJob.deadline),
                    joinedload(NotificationJob.rule),
                    joinedload(NotificationJob.vk_chat).joinedload(VKChat.community),
                )
                .filter(NotificationJob.id == job_id)
                .one_or_none()
            )
            if job is None or job.status == NotificationJobStatus.sent.value:
                continue

            if dry_run:
                job.status = NotificationJobStatus.retry.value
                job.last_error = "Dry run: message was not sent"
                db.commit()
                sent_or_updated += 1
                continue

            result = sender.send_job(job)
            if result.ok:
                job.status = NotificationJobStatus.sent.value
                job.sent_at = datetime.now(timezone.utc)
                job.vk_message_id = result.message_id
                job.last_error = None
            else:
                job.attempts += 1
                job.last_error = result.error
                job.status = (
                    NotificationJobStatus.failed.value
                    if job.attempts > settings.max_notification_attempts
                    else NotificationJobStatus.retry.value
                )
            db.commit()
            sent_or_updated += 1

    return sent_or_updated


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    count = send_due_notifications(limit=args.limit, dry_run=args.dry_run)
    print(f"processed: {count}")

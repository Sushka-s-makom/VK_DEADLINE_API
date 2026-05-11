from datetime import datetime, timezone

from sqlalchemy.orm import joinedload

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import NotificationJob, NotificationJobStatus, VKChat
from app.services.notification_job_service import get_due_jobs
from app.services.vk_sender import VKSender
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.enqueue_due_notification_jobs")
def enqueue_due_notification_jobs() -> int:
    with SessionLocal() as db:
        jobs = get_due_jobs(db)
        job_ids = []
        for job in jobs:
            job.status = NotificationJobStatus.processing.value
            job_ids.append(job.id)
        db.commit()

    for job_id in job_ids:
        send_notification_job.delay(job_id)
    return len(job_ids)


@celery_app.task(name="app.workers.tasks.send_notification_job")
def send_notification_job(job_id: int) -> dict[str, str | int | None]:
    settings = get_settings()
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
        if job is None:
            return {"status": "missing", "job_id": job_id}
        if job.status == NotificationJobStatus.sent.value:
            return {"status": "already_sent", "job_id": job_id}

        result = VKSender().send_job(job)
        if result.ok:
            job.status = NotificationJobStatus.sent.value
            job.sent_at = datetime.now(timezone.utc)
            job.vk_message_id = result.message_id
            job.last_error = None
        else:
            job.attempts += 1
            job.last_error = result.error
            if job.attempts > settings.max_notification_attempts:
                job.status = NotificationJobStatus.failed.value
            else:
                job.status = NotificationJobStatus.retry.value
        db.commit()
        return {"status": job.status, "job_id": job.id, "vk_message_id": job.vk_message_id}

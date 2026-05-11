from app.workers.tasks import enqueue_due_notification_jobs


def tick() -> int:
    """Manual scheduler entrypoint for local checks outside Celery beat."""
    return enqueue_due_notification_jobs.delay().get()

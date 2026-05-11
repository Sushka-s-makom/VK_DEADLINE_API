from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("vk_deadline_api", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "enqueue-due-notification-jobs-every-minute": {
        "task": "app.workers.tasks.enqueue_due_notification_jobs",
        "schedule": 60.0,
    }
}

celery_app.autodiscover_tasks(["app.workers"])

import os
from celery import Celery
from app.core.config import settings

# Use Redis as broker and backend
celery_app = Celery(
    "task_manager",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.task_export"]
)

# Optional: configure
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
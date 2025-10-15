from celery import Celery
from app.core.config import settings
from app.core.logging_config import setup_logging
from urllib.parse import urlparse

# Setup structured logging for Celery
setup_logging(log_level=settings.LOG_LEVEL)

# Configure broker and backend URLs with SSL if needed
broker_url = settings.REDIS_URL
backend_url = settings.REDIS_URL

# If using rediss:// (SSL), add SSL options
if settings.REDIS_URL.startswith("rediss://"):
    broker_url += "?ssl_cert_reqs=CERT_REQUIRED"
    backend_url += "?ssl_cert_reqs=CERT_REQUIRED"

# Initialize Celery app with configured URLs
celery_app = Celery(
    "task_manager",
    broker=broker_url,
    backend=backend_url,
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
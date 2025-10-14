import io
import csv
import json
from uuid import UUID
from celery import current_app as celery
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.models.task import Task
from app.db.redis import redis_client
import jwt
from datetime import datetime, timedelta, timezone
import asyncio

from app.core.email import send_csv_export_email
from app.models.user import User
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Celery workers run in different processes than FastAPI (can't share session)
# Configure engine with proper pooling for async context
engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=False,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
)
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autoflush=False,  # Prevent automatic flushes
)

@celery.task(bind=True)  # bind gives access to self
def export_task_to_csv(self, task_id: str, org_id: str):
    logger.info("CSV export started", extra={"task_id": task_id, "org_id": org_id, "celery_task_id": self.request.id})

    async def _export():
        # Create a fresh session for this task
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(Task)
                    .where(Task.id == UUID(task_id), Task.org_id == UUID(org_id))
                )
                task = result.scalars().first()
                
                if not task:
                    logger.error("Task not found for export", extra={"task_id": task_id, "org_id": org_id})
                    raise ValueError(f"Task {task_id} not found in organization {org_id}")

                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["ID", "Title", "Description", "Status", "Assignee ID", "Due Date", "Created At", "Created By"])

                writer.writerow([
                    str(task.id),
                    task.title,
                    task.description or "",
                    task.status,
                    str(task.assignee_id) if task.assignee_id else "",
                    task.due_date.isoformat() if task.due_date else "",
                    task.created_at.isoformat(),
                    str(task.created_by_id)
                ])

                csv_data = output.getvalue()
                output.close()

                csv_key = f"csv_export:task:{task_id}:{self.request.id}"
                await redis_client.setex(csv_key, 3600, csv_data)
                
                logger.info("CSV generated and stored", extra={"task_id": task_id, "csv_key": csv_key})

                download_token = jwt.encode(
                    {
                        "csv_key": csv_key,
                        "task_id": task_id,
                        "org_id": org_id,
                        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
                    },
                    settings.SECRET_KEY,
                    algorithm=settings.ALGORITHM
                )
                
                download_url = f"{settings.BASE_URL}/tasks/download/{download_token}"
                
                # Fetch admin email
                admin_result = await db.execute(
                    select(User.email)
                    .where(User.org_id == UUID(org_id), User.role == "admin")
                    .limit(1)
                )
                admin_email = admin_result.scalar_one_or_none()

                # Session will be automatically closed by context manager
                
            except Exception as e:
                logger.error("CSV export failed", extra={"task_id": task_id, "org_id": org_id, "error": str(e)})
                raise
        
        # Send email AFTER database session is closed
        if admin_email:
            send_csv_export_email(admin_email, download_url)
            logger.info("CSV export email sent", extra={"task_id": task_id, "admin_email": admin_email})
        else:
            logger.warning("No admin email found", extra={"org_id": org_id, "task_id": task_id})

        return download_url

    # Run async function in Celery task
    return asyncio.run(_export())
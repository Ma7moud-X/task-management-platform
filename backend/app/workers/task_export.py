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

# Celery workers run in different processes than FastAPI (can't share session)
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@celery.task(bind=True) # bind give access to self
def export_task_to_csv(self, task_id: str, org_id: str):

    async def _export():
        db = AsyncSessionLocal()
        try:
            result = await db.execute(
                select(Task)
                .where(Task.id == UUID(task_id), Task.org_id == UUID(org_id))
            )
            task = result.scalars().first()
            
            if not task:
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
            
            # In real GCP: email service
            download_url = f"http://localhost:8000/tasks/download/{download_token}"
            print(f"[EMAIL SIMULATION] CSV export ready for task {task_id}. Download: {download_url}")

            return download_url

        except Exception as e:
            print(f"[ERROR] CSV export failed for task {task_id}: {str(e)}")
            raise
        finally:
            await db.close()

    # Run async function in Celery task
    return asyncio.run(_export())
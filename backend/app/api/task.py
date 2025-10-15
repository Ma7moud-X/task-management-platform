from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

import jwt
from app.core.security import require_admin, require_member
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.schemas.auth import UserRole
from app.services.task import create_task, get_tasks, publish_task_event, update_task, delete_task
from app.db.session import get_db
from app.db.redis import redis_client
from app.core.config import settings
from celery_app import celery_app
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/organizations/{org_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task_endpoint(org_id: UUID, task_in: TaskCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    logger.info("Creating task", extra={"org_id": str(org_id), "user_id": current_user["user_id"], "title": task_in.title})
    
    if str(current_user["org_id"]) != str(org_id):
        logger.warning("Tenant mismatch", extra={"user_org": current_user["org_id"], "requested_org": str(org_id)})
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    task = await create_task(
        db=db,
        obj_in=task_in,
        org_id=org_id,
        creator_id=UUID(current_user["user_id"])
    )
    await publish_task_event(
        org_id=str(task.org_id),
        event_type="created",
        task_data=TaskResponse.model_validate(task).model_dump(mode='json')
    )
    
    logger.info("Task created", extra={"task_id": str(task.id), "org_id": str(org_id)})
    return task

@router.get("/organizations/{org_id}/tasks", response_model=list[TaskResponse])
async def list_tasks(org_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_member), 
    status: str | None = Query(None), assignee_id: UUID | None = Query(None), page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    
    logger.info("Listing tasks", extra={"org_id": str(org_id), "page": page, "size": size})
    
    if str(current_user["org_id"]) != str(org_id):
        logger.warning("Tenant mismatch on list", extra={"user_org": current_user["org_id"], "requested_org": str(org_id)})
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    skip = (page - 1) * size
    tasks = await get_tasks(
        db=db,
        org_id=org_id,
        current_user_id=UUID(current_user["user_id"]),
        role=UserRole(current_user["role"]),
        status=status,
        assignee_id=assignee_id,
        skip=skip,
        limit=size
    )
    logger.info("Tasks retrieved", extra={"org_id": str(org_id), "count": len(tasks)})
    return tasks

@router.post("/tasks/{task_id}/export", status_code=status.HTTP_202_ACCEPTED)
async def trigger_task_export(task_id: UUID, current_user: dict = Depends(require_member)):
    logger.info("Export triggered", extra={"task_id": str(task_id), "user_id": current_user["user_id"]})
    
    task = celery_app.send_task(
        "app.workers.task_export.export_task_to_csv",
        args=[str(task_id), str(current_user["org_id"])]
    )
    
    return {
        "message": "CSV export started",
        "task_id": str(task_id),
        "celery_task_id": task.id
    }

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task_endpoint(task_id: UUID, task_update: TaskUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_member)):
    logger.info("Updating task", extra={"task_id": str(task_id), "user_id": current_user["user_id"]})
    
    task = await update_task(
        db=db,
        task_id=task_id,
        obj_in=task_update,
        org_id=UUID(current_user["org_id"]),
        current_user_id=UUID(current_user["user_id"]),
        role=UserRole(current_user["role"])
    )
    await publish_task_event(
        org_id=str(task.org_id),
        event_type="updated",
        task_data=TaskResponse.model_validate(task).model_dump(mode='json')
    )
    logger.info("Task updated", extra={"task_id": str(task_id)})
    return task

@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_endpoint(task_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    logger.info("Deleting task", extra={"task_id": str(task_id), "user_id": current_user["user_id"]})
    
    task = await delete_task(
        db=db,
        task_id=task_id,
        org_id=UUID(current_user["org_id"]),
        current_user_id=UUID(current_user["user_id"]),
        role=UserRole(current_user["role"])
    )
    await publish_task_event(
        org_id=str(task.org_id),
        event_type="deleted",
        task_data=TaskResponse.model_validate(task).model_dump(mode='json')
    )
    logger.info("Task deleted", extra={"task_id": str(task_id)})
    return None

@router.get("/tasks/download/{token}")
async def download_task_csv(token: str):
    logger.info("Download attempt", extra={"token_preview": token[:10]})
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        csv_key = payload["csv_key"]
        task_id = payload["task_id"]
    except jwt.ExpiredSignatureError:
        logger.warning("Download link expired", extra={"token_preview": token[:10]})
        raise HTTPException(status_code=400, detail="Download link expired")
    except (jwt.InvalidTokenError, KeyError):
        logger.error("Invalid download token", extra={"token_preview": token[:10]})
        raise HTTPException(status_code=400, detail="Invalid download token")

    csv_data = await redis_client.get(csv_key)
    if not csv_data:
        logger.warning("Export not found", extra={"csv_key": csv_key, "task_id": task_id})
        raise HTTPException(status_code=404, detail="Export not found or expired")

    logger.info("Download successful", extra={"task_id": task_id})
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=task_{task_id}_export.csv"}
    )
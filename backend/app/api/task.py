from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.security import require_admin, require_member
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskStatus
from app.schemas.auth import UserRole
from app.services.task import create_task, get_tasks, update_task, delete_task
from app.db.session import get_db

router = APIRouter()


@router.post("/organizations/{org_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task_endpoint(org_id: UUID, task_in: TaskCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_member)):
    
    if str(current_user["org_id"]) != str(org_id):
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    task = await create_task(
        db=db,
        obj_in=task_in,
        org_id=org_id,
        creator_id=UUID(current_user["user_id"])
    )
    return task

@router.get("/organizations/{org_id}/tasks", response_model=list[TaskResponse])
async def list_tasks(org_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_member), 
    status: str | None = Query(None), assignee_id: UUID | None = Query(None), page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    
    if str(current_user["org_id"]) != str(org_id):
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
    return tasks

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task_endpoint(task_id: UUID, task_update: TaskUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_member)):
    # Tenant checking is done in the service layer by verifying task.org_id matches current_user's org_id
    task = await update_task(
        db=db,
        task_id=task_id,
        obj_in=task_update,
        org_id=UUID(current_user["org_id"]),
        current_user_id=UUID(current_user["user_id"]),
        role=UserRole(current_user["role"])
    )
    return task

@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_endpoint(task_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    # Tenant checking is done in the service layer by verifying task.org_id matches current_user's org_id
    await delete_task(
        db=db,
        task_id=task_id,
        org_id=UUID(current_user["org_id"]),
        current_user_id=UUID(current_user["user_id"]),
        role=UserRole(current_user["role"])
    )
    return None
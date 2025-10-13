from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional
from fastapi import HTTPException, status

from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskStatus
from app.schemas.auth import UserRole
from app.db.redis import redis_client
import json


async def create_task(db: AsyncSession, 
    *, obj_in: TaskCreate, org_id: UUID, creator_id: UUID) -> Task:
    
    # Validate assignee exists in the same organization if provided
    if obj_in.assignee_id:
        result = await db.execute(
            select(User).where(User.id == obj_in.assignee_id, User.org_id == org_id)
        )
        assignee = result.scalars().first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee not found in your organization"
            )
    
    db_obj = Task(
        **obj_in.model_dump(exclude_unset=True),
        org_id=org_id,
        created_by_id=creator_id
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_tasks(db: AsyncSession,
    *, org_id: UUID, current_user_id: UUID, role: UserRole, status: Optional[TaskStatus] = None, assignee_id: Optional[UUID] = None, skip: int = 0, limit: int = 100) -> list[Task]:
    
    # Base query - all tasks in the organization
    query = select(Task).where(Task.org_id == org_id)

    if status:
        query = query.where(Task.status == status)
    
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)

    if role == UserRole.MEMBER:
        query = query.where(Task.assignee_id == current_user_id)

    # Order by created_at descending (newest first)
    query = query.order_by(Task.created_at.desc())
    
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()

async def get_task_by_id(db: AsyncSession,
    *, task_id: UUID, org_id: UUID, current_user_id: UUID, role: UserRole) -> Optional[Task]:

    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.org_id == org_id
        )
    )
    task = result.scalars().first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Members can only access their own tasks
    if role == UserRole.MEMBER and task.assignee_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this task"
        )
    
    return task

async def update_task(db: AsyncSession,
    *, task_id: UUID, obj_in: TaskUpdate, org_id: UUID, current_user_id: UUID, role: UserRole) -> Task:

    # Get existing task with access control
    task = await get_task_by_id(
        db=db,
        task_id=task_id,
        org_id=org_id,
        current_user_id=current_user_id,
        role=role
    )
    
    # Validate assignee if being updated
    update_data = obj_in.model_dump(exclude_unset=True)
    
    if role == UserRole.MEMBER:
        # Check if member is trying to update fields other than status
        non_status_fields = {k for k in update_data.keys() if k != "status"}
        if non_status_fields:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Members can only update task status"
            )
            
    if "assignee_id" in update_data and update_data["assignee_id"]:
        result = await db.execute(
            select(User).where(
                User.id == update_data["assignee_id"],
                User.org_id == org_id
            )
        )
        assignee = result.scalars().first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee not found in your organization"
            )
    
    # Update task fields
    for field, value in update_data.items():
        setattr(task, field, value)
    
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

async def delete_task(db: AsyncSession,
    *, task_id: UUID, org_id: UUID, current_user_id: UUID, role: UserRole) -> Task:
    
    # Only admins can delete tasks
    if role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete tasks"
        )
    
    # Get existing task
    task = await get_task_by_id(
        db=db,
        task_id=task_id,
        org_id=org_id,
        current_user_id=current_user_id,
        role=role
    )
    
    await db.delete(task)
    await db.commit()
    return task
    


async def publish_task_event(org_id: str, event_type: str, task_data: dict):
    channel = f"org:{org_id}:tasks"
    message = {
        "event": event_type,  # "created", "updated", "deleted"
        "data": task_data
    }
    await redis_client.publish(channel, json.dumps(message, default=str))
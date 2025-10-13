from sqlalchemy import String, Column, ForeignKey, Enum as SQLAlchemyEnum, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base
from app.schemas.task import TaskStatus
from sqlalchemy.sql import func

class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLAlchemyEnum(TaskStatus, name="task_status"), nullable=False, default=TaskStatus.TODO)
    due_date = Column(DateTime(timezone=True), nullable=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks", foreign_keys=[assignee_id], lazy="selectin")
    creator = relationship("User", back_populates="created_tasks", foreign_keys=[created_by_id])
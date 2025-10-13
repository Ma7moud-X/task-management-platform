from sqlalchemy import String, Column, ForeignKey, Enum as SQLAlchemyEnum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.schemas.auth import UserRole
from app.db.base import Base
from sqlalchemy.sql import func



class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLAlchemyEnum(UserRole, name="user_role"), nullable=False, default=UserRole.MEMBER)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    organization = relationship("Organization", back_populates="users")
    tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id", lazy="selectin")
    created_tasks = relationship("Task", back_populates="creator", foreign_keys="Task.created_by_id")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

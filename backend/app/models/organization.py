from sqlalchemy import String, Column, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    users = relationship("User", back_populates="organization")
    tasks = relationship("Task", back_populates="organization", lazy="selectin")
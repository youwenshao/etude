"""Job model."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.types import DialectJSON


class JobStatus(PyEnum):
    """Job status enumeration."""

    PENDING = "pending"
    OMR_PROCESSING = "omr_processing"
    OMR_COMPLETED = "omr_completed"
    OMR_FAILED = "omr_failed"
    FINGERING_PROCESSING = "fingering_processing"
    FINGERING_COMPLETED = "fingering_completed"
    FINGERING_FAILED = "fingering_failed"
    RENDERING_PROCESSING = "rendering_processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStage(PyEnum):
    """Job stage enumeration."""

    OMR = "omr"
    FINGERING = "fingering"
    RENDERING = "rendering"


class Job(Base):
    """Job model for tracking pipeline execution."""

    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(50), default=JobStatus.PENDING.value, nullable=False, index=True)
    stage = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    job_metadata = Column(DialectJSON, default=dict, nullable=False)

    # Relationships
    user = relationship("User", backref="jobs")
    artifacts = relationship("Artifact", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, status={self.status}, stage={self.stage})>"


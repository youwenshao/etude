"""Artifact model."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.types import DialectJSON


class ArtifactType(PyEnum):
    """Artifact type enumeration."""

    PDF = "pdf"
    IR_V1 = "ir_v1"
    IR_V2 = "ir_v2"
    MUSICXML = "musicxml"
    MIDI = "midi"
    SVG = "svg"


class Artifact(Base):
    """Artifact model for storing file metadata."""

    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True)
    artifact_type = Column(String(50), nullable=False, index=True)
    schema_version = Column(String(20), nullable=False, default="1.0.0")
    storage_path = Column(String(512), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    checksum = Column(String(64), nullable=False)  # SHA256 hex
    artifact_metadata = Column(DialectJSON, default=dict, nullable=False)
    parent_artifact_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    job = relationship("Job", back_populates="artifacts")
    parent_artifact = relationship("Artifact", remote_side=[id], backref="child_artifacts")

    def __repr__(self) -> str:
        return f"<Artifact(id={self.id}, type={self.artifact_type}, job_id={self.job_id})>"


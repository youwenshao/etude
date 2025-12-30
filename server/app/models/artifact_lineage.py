"""Artifact lineage model for tracking transformations."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ArtifactLineage(Base):
    """Artifact lineage model for tracking transformation relationships."""

    __tablename__ = "artifact_lineage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    source_artifact_id = Column(
        UUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=False, index=True
    )
    derived_artifact_id = Column(
        UUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=False, index=True
    )
    transformation_type = Column(String(100), nullable=False)
    transformation_version = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<ArtifactLineage(id={self.id}, "
            f"source={self.source_artifact_id}, "
            f"derived={self.derived_artifact_id})>"
        )


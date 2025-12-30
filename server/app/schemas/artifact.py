"""Artifact schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ArtifactBase(BaseModel):
    """Base artifact schema."""

    artifact_type: str
    schema_version: str = "1.0.0"
    artifact_metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactCreate(ArtifactBase):
    """Schema for creating an artifact."""

    job_id: UUID
    parent_artifact_id: UUID | None = None


class ArtifactResponse(ArtifactBase):
    """Schema for artifact response."""

    id: UUID
    job_id: UUID
    storage_path: str
    file_size: int
    checksum: str
    parent_artifact_id: UUID | None
    created_at: datetime

    class Config:
        from_attributes = True


class ArtifactLineageResponse(BaseModel):
    """Schema for artifact lineage graph."""

    artifact: ArtifactResponse
    ancestors: list[ArtifactResponse] = Field(default_factory=list)
    descendants: list[ArtifactResponse] = Field(default_factory=list)


"""Job schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.job import JobStatus, JobStage


class JobBase(BaseModel):
    """Base job schema."""

    stage: JobStage | None = None
    job_metadata: dict[str, Any] = Field(default_factory=dict)


class JobCreate(JobBase):
    """Schema for creating a job."""

    pass


class JobUpdate(BaseModel):
    """Schema for updating a job."""

    status: JobStatus | None = None
    stage: JobStage | None = None
    error_message: str | None = None
    job_metadata: dict[str, Any] | None = None


class JobResponse(JobBase):
    """Schema for job response."""

    id: UUID
    user_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    error_message: str | None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Schema for paginated job list response."""

    items: list[JobResponse]
    total: int
    page: int
    page_size: int


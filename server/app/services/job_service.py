"""Job service for managing job lifecycle."""

import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus, JobStage
from app.models.artifact import Artifact, ArtifactType
from app.core.state_machine import validate_transition
from app.services.storage_service import storage_service
from app.config import settings


class JobService:
    """Service for job management operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize job service with database session."""
        self.db = db

    async def create_job(self, user_id: UUID, pdf_file: bytes, filename: str = "upload.pdf") -> Job:
        """
        Create a new job and store PDF as artifact.

        Args:
            user_id: User ID creating the job
            pdf_file: PDF file content as bytes
            filename: Original filename

        Returns:
            Created Job instance
        """
        # Create job
        job = Job(
            user_id=user_id,
            status=JobStatus.PENDING.value,
            stage=JobStage.OMR.value,
            job_metadata={"filename": filename, "created_at": datetime.utcnow().isoformat()},
        )
        self.db.add(job)
        await self.db.flush()  # Get job.id

        # Store PDF as artifact
        checksum = hashlib.sha256(pdf_file).hexdigest()
        storage_key = f"jobs/{job.id}/artifacts/{job.id}_pdf.pdf"
        await storage_service.upload_file(
            pdf_file, storage_key, settings.MINIO_BUCKET_PDFS, content_type="application/pdf"
        )

        artifact = Artifact(
            job_id=job.id,
            artifact_type=ArtifactType.PDF.value,
            schema_version="1.0.0",
            storage_path=storage_key,
            file_size=len(pdf_file),
            checksum=checksum,
            artifact_metadata={"filename": filename, "original_upload": True},
        )
        self.db.add(artifact)

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_job(self, job_id: UUID) -> Job | None:
        """Get job by ID."""
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def list_user_jobs(
        self,
        user_id: UUID,
        status: str | None = None,
        stage: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        """
        List jobs for a user with filtering and pagination.

        Returns:
            Tuple of (jobs list, total count)
        """
        query = select(Job).where(Job.user_id == user_id)

        if status:
            query = query.where(Job.status == status)
        if stage:
            query = query.where(Job.stage == stage)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        query = query.order_by(Job.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        jobs = result.scalars().all()

        return list(jobs), total

    async def update_job_status(
        self, job_id: UUID, status: JobStatus, error_message: str | None = None
    ) -> Job:
        """
        Update job status with validation.

        Args:
            job_id: Job ID
            status: New status
            error_message: Optional error message

        Returns:
            Updated Job instance

        Raises:
            ValueError: If transition is invalid
        """
        job = await self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        is_valid, error = validate_transition(job.status, status.value)
        if not is_valid:
            raise ValueError(error)

        job.status = status.value
        if error_message:
            job.error_message = error_message
        if status == JobStatus.COMPLETED:
            job.completed_at = datetime.utcnow()

        # Update metadata with transition history
        if "transitions" not in job.job_metadata:
            job.job_metadata["transitions"] = []
        old_status = job.status
        job.job_metadata["transitions"].append(
            {
                "from": old_status,
                "to": status.value,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def record_error(self, job_id: UUID, error_message: str) -> Job:
        """Record an error for a job."""
        job = await self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        job.error_message = error_message
        job.status = JobStatus.FAILED.value
        job.completed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_job_artifacts(self, job_id: UUID) -> list[Artifact]:
        """Get all artifacts for a job."""
        result = await self.db.execute(
            select(Artifact).where(Artifact.job_id == job_id).order_by(Artifact.created_at)
        )
        return list(result.scalars().all())

    async def delete_job(self, job_id: UUID) -> bool:
        """
        Delete a job and all its artifacts.

        Returns:
            True if deleted, False if not found
        """
        job = await self.get_job(job_id)
        if not job:
            return False

        # Get all artifacts
        artifacts = await self.get_job_artifacts(job_id)

        # Delete from storage
        for artifact in artifacts:
            bucket = (
                settings.MINIO_BUCKET_PDFS
                if artifact.artifact_type == ArtifactType.PDF.value
                else settings.MINIO_BUCKET_ARTIFACTS
            )
            await storage_service.delete_file(artifact.storage_path, bucket)

        # Delete from database (cascade will handle artifacts)
        await self.db.delete(job)
        await self.db.commit()
        return True


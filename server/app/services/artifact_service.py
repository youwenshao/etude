"""Artifact service for managing artifacts and lineage."""

import hashlib
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.models.artifact_lineage import ArtifactLineage
from app.services.storage_service import storage_service
from app.config import settings


class ArtifactService:
    """Service for artifact management and lineage tracking."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize artifact service with database session."""
        self.db = db

    def _get_file_extension(self, artifact_type: str) -> str:
        """Get file extension for artifact type."""
        extensions = {
            "pdf": "pdf",
            "ir_v1": "json",
            "ir_v2": "json",
            "musicxml": "musicxml",
            "midi": "midi",
            "svg": "svg",
        }
        return extensions.get(artifact_type, "bin")

    async def store_artifact(
        self,
        job_id: UUID,
        artifact_type: str,
        data: bytes,
        metadata: dict[str, Any],
        parent_artifact_id: UUID | None = None,
        schema_version: str = "1.0.0",
    ) -> Artifact:
        """
        Store an artifact in object storage and database.

        Args:
            job_id: Job ID
            artifact_type: Type of artifact
            data: Artifact data as bytes
            metadata: Additional metadata
            parent_artifact_id: Optional parent artifact ID for lineage
            schema_version: Schema version string

        Returns:
            Created Artifact instance
        """
        # Calculate checksum
        checksum = hashlib.sha256(data).hexdigest()

        # Generate storage key
        artifact_id = UUID(int=0)  # Placeholder, will be replaced after creation
        ext = self._get_file_extension(artifact_type)
        storage_key = f"jobs/{job_id}/artifacts/{artifact_id}.{ext}"

        # Determine bucket
        bucket = (
            settings.MINIO_BUCKET_PDFS
            if artifact_type == "pdf"
            else settings.MINIO_BUCKET_ARTIFACTS
        )

        # Upload to storage
        content_type_map = {
            "pdf": "application/pdf",
            "ir_v1": "application/json",
            "ir_v2": "application/json",
            "musicxml": "application/xml",
            "midi": "audio/midi",
            "svg": "image/svg+xml",
        }
        content_type = content_type_map.get(artifact_type, "application/octet-stream")

        await storage_service.upload_file(data, storage_key, bucket, content_type=content_type)

        # Create database record (we'll update storage_path after getting ID)
        artifact = Artifact(
            job_id=job_id,
            artifact_type=artifact_type,
            schema_version=schema_version,
            storage_path=storage_key,  # Temporary, will update
            file_size=len(data),
            checksum=checksum,
            artifact_metadata=metadata,
            parent_artifact_id=parent_artifact_id,
        )
        self.db.add(artifact)
        await self.db.flush()  # Get artifact.id

        # Update storage key with actual artifact ID and re-upload
        actual_storage_key = f"jobs/{job_id}/artifacts/{artifact.id}.{ext}"
        if actual_storage_key != storage_key:
            # Re-upload with correct path
            await storage_service.upload_file(data, actual_storage_key, bucket, content_type=content_type)
            # Delete old file
            await storage_service.delete_file(storage_key, bucket)
            artifact.storage_path = actual_storage_key

        # Record lineage if parent exists
        if parent_artifact_id:
            lineage = ArtifactLineage(
                source_artifact_id=parent_artifact_id,
                derived_artifact_id=artifact.id,
                transformation_type=artifact_type,
                transformation_version=schema_version,
            )
            self.db.add(lineage)

        await self.db.commit()
        await self.db.refresh(artifact)
        return artifact

    async def get_artifact(self, artifact_id: UUID) -> tuple[Artifact, bytes] | None:
        """
        Get artifact metadata and data.

        Returns:
            Tuple of (Artifact, data bytes) or None if not found
        """
        result = await self.db.execute(select(Artifact).where(Artifact.id == artifact_id))
        artifact = result.scalar_one_or_none()
        if not artifact:
            return None

        # Determine bucket
        bucket = (
            settings.MINIO_BUCKET_PDFS
            if artifact.artifact_type == "pdf"
            else settings.MINIO_BUCKET_ARTIFACTS
        )

        # Download data
        data = await storage_service.download_file(artifact.storage_path, bucket)
        return artifact, data

    async def get_artifact_by_job_and_type(
        self, job_id: UUID, artifact_type: str
    ) -> Artifact | None:
        """Get the latest artifact of a specific type for a job."""
        result = await self.db.execute(
            select(Artifact)
            .where(Artifact.job_id == job_id)
            .where(Artifact.artifact_type == artifact_type)
            .order_by(Artifact.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_artifact_lineage(self, artifact_id: UUID) -> dict[str, list[Artifact]]:
        """
        Get artifact lineage (ancestors and descendants).

        Returns:
            Dictionary with 'ancestors' and 'descendants' lists
        """
        # Get ancestors (artifacts this was derived from)
        ancestors_result = await self.db.execute(
            select(Artifact)
            .join(ArtifactLineage, Artifact.id == ArtifactLineage.source_artifact_id)
            .where(ArtifactLineage.derived_artifact_id == artifact_id)
        )
        ancestors = list(ancestors_result.scalars().all())

        # Get descendants (artifacts derived from this)
        descendants_result = await self.db.execute(
            select(Artifact)
            .join(ArtifactLineage, Artifact.id == ArtifactLineage.derived_artifact_id)
            .where(ArtifactLineage.source_artifact_id == artifact_id)
        )
        descendants = list(descendants_result.scalars().all())

        return {"ancestors": ancestors, "descendants": descendants}


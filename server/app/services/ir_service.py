"""IR service for managing Symbolic Score IR artifacts."""

import hashlib
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact, ArtifactType
from app.models.artifact_lineage import ArtifactLineage
from app.schemas.symbolic_ir import SchemaRegistry
from app.schemas.symbolic_ir.v1.schema import SymbolicScoreIR
from app.services.storage_service import storage_service
from app.config import settings


class IRService:
    """
    Service for managing Symbolic IR artifacts.
    Handles serialization, validation, storage, and retrieval.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize IR service with database session."""
        self.db = db

    async def store_ir(
        self,
        job_id: UUID,
        ir: SymbolicScoreIR,
        parent_artifact_id: Optional[UUID] = None,
    ) -> Artifact:
        """
        Store an IR as an artifact with proper versioning.

        Args:
            job_id: Job ID
            ir: SymbolicScoreIR instance
            parent_artifact_id: Optional parent artifact ID for lineage

        Returns:
            Created Artifact instance
        """
        # Serialize IR to JSON
        ir_json = ir.to_json(indent=2)
        ir_bytes = ir_json.encode("utf-8")

        # Calculate checksum
        checksum = hashlib.sha256(ir_bytes).hexdigest()

        # Prepare metadata
        metadata = {
            "schema_version": ir.version,
            "schema_type": ir.schema_type,
            "note_count": len(ir.notes),
            "chord_count": len(ir.chords),
            "generated_by": ir.metadata.generated_by.model_dump(),
            "average_confidence": ir.metadata.average_detection_confidence,
            "title": ir.metadata.title,
            "composer": ir.metadata.composer,
        }

        # Generate storage key
        artifact_id = UUID(int=0)  # Placeholder, will be replaced after creation
        storage_key = f"jobs/{job_id}/ir/v1/{artifact_id}.json"

        # Determine bucket
        bucket = settings.MINIO_BUCKET_ARTIFACTS

        # Upload to storage
        await storage_service.upload_file(
            file=ir_bytes,
            key=storage_key,
            bucket=bucket,
            content_type="application/json",
        )

        # Create database record
        artifact = Artifact(
            job_id=job_id,
            artifact_type=ArtifactType.IR_V1.value,
            schema_version=ir.version,
            storage_path=storage_key,  # Temporary, will update
            file_size=len(ir_bytes),
            checksum=checksum,
            artifact_metadata=metadata,
            parent_artifact_id=parent_artifact_id,
        )
        self.db.add(artifact)
        await self.db.flush()  # Get artifact.id

        # Update storage key with actual artifact ID and re-upload
        actual_storage_key = f"jobs/{job_id}/ir/v1/{artifact.id}.json"
        if actual_storage_key != storage_key:
            # Re-upload with correct path
            await storage_service.upload_file(
                file=ir_bytes,
                key=actual_storage_key,
                bucket=bucket,
                content_type="application/json",
            )
            # Delete old file
            await storage_service.delete_file(storage_key, bucket)
            artifact.storage_path = actual_storage_key

        # Record lineage if parent exists
        if parent_artifact_id:
            lineage = ArtifactLineage(
                source_artifact_id=parent_artifact_id,
                derived_artifact_id=artifact.id,
                transformation_type="omr_to_ir",
                transformation_version=ir.version,
            )
            self.db.add(lineage)

        await self.db.commit()
        await self.db.refresh(artifact)

        return artifact

    async def load_ir(
        self,
        artifact_id: UUID,
    ) -> Tuple[Artifact, SymbolicScoreIR]:
        """
        Load an IR from storage and validate it.

        Args:
            artifact_id: Artifact UUID

        Returns:
            Tuple of (Artifact, SymbolicScoreIR)

        Raises:
            ValueError: If artifact not found or checksum mismatch
        """
        # Get artifact metadata
        result = await self.db.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()

        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")

        # Download from storage
        bucket = settings.MINIO_BUCKET_ARTIFACTS
        ir_bytes = await storage_service.download_file(
            key=artifact.storage_path,
            bucket=bucket,
        )

        # Verify checksum
        checksum = hashlib.sha256(ir_bytes).hexdigest()
        if checksum != artifact.checksum:
            raise ValueError(f"Checksum mismatch for artifact {artifact_id}")

        # Deserialize and validate
        ir_json = ir_bytes.decode("utf-8")

        # Get appropriate schema version
        schema_class = SchemaRegistry.get_schema(artifact.schema_version)
        ir = schema_class.from_json(ir_json)

        return artifact, ir

    async def validate_ir(self, ir_data: dict) -> SymbolicScoreIR:
        """
        Validate IR data against schema.

        Args:
            ir_data: Dictionary containing IR data

        Returns:
            Validated SymbolicScoreIR instance

        Raises:
            ValueError: If validation fails
        """
        version = ir_data.get("version", "1.0.0")
        schema_class = SchemaRegistry.get_schema(version)
        return schema_class.model_validate(ir_data)

    async def get_ir_by_job(
        self,
        job_id: UUID,
        artifact_type: ArtifactType = ArtifactType.IR_V1,
    ) -> Optional[Tuple[Artifact, SymbolicScoreIR]]:
        """
        Get the most recent IR of a specific type for a job.

        Args:
            job_id: Job UUID
            artifact_type: Artifact type (default: IR_V1)

        Returns:
            Tuple of (Artifact, SymbolicScoreIR) or None if not found
        """
        result = await self.db.execute(
            select(Artifact)
            .where(
                Artifact.job_id == job_id,
                Artifact.artifact_type == artifact_type.value,
            )
            .order_by(Artifact.created_at.desc())
            .limit(1)
        )
        artifact = result.scalar_one_or_none()

        if not artifact:
            return None

        return await self.load_ir(artifact.id)


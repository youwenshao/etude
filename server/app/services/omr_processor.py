"""Background task processor for OMR job processing."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.state_machine import JobStatus
from app.models.artifact import ArtifactType
from app.schemas.symbolic_ir import SchemaRegistry
from app.services.ir_service import IRService
from app.services.job_service import JobService
from app.services.omr_client import get_omr_client
from app.services.storage_service import storage_service
from app.config import settings

logger = logging.getLogger(__name__)


async def process_omr_job(job_id: UUID, db: AsyncSession) -> None:
    """
    Background task to process a job through OMR service.

    This function:
    1. Downloads PDF from storage
    2. Calls OMR service to process PDF
    3. Validates and stores IR artifact
    4. Updates job status
    5. Creates artifact lineage

    Args:
        job_id: Job UUID to process
        db: Database session
    """
    job_service = JobService(db)
    ir_service = IRService(db)
    omr_client = get_omr_client()

    try:
        # Get job
        job = await job_service.get_job(job_id)
        if not job:
            logger.error(f"Job not found: {job_id}")
            return

        # Update status to OMR_PROCESSING
        await job_service.update_job_status(job_id, JobStatus.OMR_PROCESSING)

        logger.info(f"Starting OMR processing for job {job_id}")

        # Get PDF artifact
        artifacts = await job_service.get_job_artifacts(job_id)
        pdf_artifact = next(
            (a for a in artifacts if a.artifact_type == ArtifactType.PDF.value), None
        )

        if not pdf_artifact:
            raise ValueError(f"No PDF artifact found for job {job_id}")

        # Download PDF from storage
        pdf_bytes = await storage_service.download_file(
            key=pdf_artifact.storage_path, bucket=settings.MINIO_BUCKET_PDFS
        )

        logger.info(
            f"Downloaded PDF for job {job_id}",
            size_bytes=len(pdf_bytes),
            artifact_id=str(pdf_artifact.id),
        )

        # Call OMR service
        result = await omr_client.process_pdf(
            pdf_bytes=pdf_bytes,
            source_pdf_artifact_id=str(pdf_artifact.id),
            filename=pdf_artifact.artifact_metadata.get("filename"),
        )

        ir_data = result["ir_data"]

        # Validate IR against schema
        schema_class = SchemaRegistry.get_schema(ir_data.get("version", "1.0.0"))
        validated_ir = schema_class.model_validate(ir_data)

        logger.info(
            f"OMR processing completed for job {job_id}",
            notes=len(validated_ir.notes),
            pages=result["processing_metadata"]["pages_processed"],
        )

        # Store IR artifact
        ir_artifact = await ir_service.store_ir(
            job_id=job_id,
            ir=validated_ir,
            parent_artifact_id=pdf_artifact.id,
        )

        logger.info(
            f"Stored IR artifact for job {job_id}",
            artifact_id=str(ir_artifact.id),
        )

        # Update job status to OMR_COMPLETED
        await job_service.update_job_status(job_id, JobStatus.OMR_COMPLETED)

        logger.info(f"OMR processing completed successfully for job {job_id}")

        # Trigger fingering inference task
        from app.tasks.fingering_tasks import process_fingering_task

        process_fingering_task.delay(
            job_id=str(job_id),
            ir_v1_artifact_id=str(ir_artifact.id),
        )

        logger.info(f"Triggered fingering inference task for job {job_id}")

    except Exception as e:
        logger.error(
            f"OMR processing failed for job {job_id}: {e}",
            exc_info=True,
        )

        # Update job status to OMR_FAILED
        try:
            await job_service.update_job_status(
                job_id, JobStatus.OMR_FAILED, error_message=str(e)
            )
        except Exception as update_error:
            logger.error(
                f"Failed to update job status to OMR_FAILED: {update_error}",
                exc_info=True,
            )


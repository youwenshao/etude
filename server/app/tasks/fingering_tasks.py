"""Celery tasks for fingering processing."""

import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.core.state_machine import JobStatus
from app.db.session import AsyncSessionLocal
from app.models.artifact import ArtifactType
from app.schemas.symbolic_ir import SchemaRegistry
from app.services.fingering_client import get_fingering_client
from app.services.ir_service import IRService
from app.services.job_service import JobService

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.process_fingering", bind=True)
def process_fingering_task(self, job_id: str, ir_v1_artifact_id: str):
    """
    Celery task to process fingering inference asynchronously.

    Args:
        job_id: UUID of the job
        ir_v1_artifact_id: UUID of the IR v1 artifact
    """
    return asyncio.run(
        process_fingering_async(self, UUID(job_id), UUID(ir_v1_artifact_id))
    )


async def process_fingering_async(
    task, job_id: UUID, ir_v1_artifact_id: UUID
):
    """Async implementation of fingering processing."""
    logger.info(f"Starting fingering inference for job {job_id}")

    try:
        async with AsyncSessionLocal() as db:
            # Initialize services
            job_service = JobService(db)
            ir_service = IRService(db)
            fingering_client = get_fingering_client()

            # Update job status
            await job_service.update_job_status(job_id, JobStatus.FINGERING_PROCESSING)

            # Load IR v1
            ir_v1_artifact, ir_v1 = await ir_service.load_ir(ir_v1_artifact_id)

            logger.info(f"Loaded IR v1: {len(ir_v1.notes)} notes")

            # Call fingering service
            ir_v1_dict = ir_v1.model_dump()

            fingering_response = await fingering_client.infer_fingering(
                ir_v1=ir_v1_dict,
                uncertainty_policy="mle",
            )

            logger.info("Fingering service processing complete")

            # Validate and store IR v2
            ir_v2_data = fingering_response["symbolic_ir_v2"]

            # Get appropriate schema version
            schema_class = SchemaRegistry.get_schema(ir_v2_data.get("version", "2.0.0"))
            ir_v2 = schema_class.model_validate(ir_v2_data)

            # Store IR v2 as artifact
            ir_v2_artifact = await ir_service.store_ir(
                job_id=job_id,
                ir=ir_v2,
                parent_artifact_id=ir_v1_artifact_id,
            )

            # Update artifact type to IR_V2
            ir_v2_artifact.artifact_type = ArtifactType.IR_V2.value
            await db.commit()

            logger.info(f"Stored IR v2 artifact: {ir_v2_artifact.id}")

            # Update job status
            await job_service.update_job_status(job_id, JobStatus.FINGERING_COMPLETED)

            # Process rendering directly to ensure job completion
            # This ensures the pipeline continues even if Celery workers aren't running
            logger.info(f"Processing rendering directly for job {job_id}")
            try:
                from app.tasks.rendering_tasks import process_rendering_async

                await process_rendering_async(job_id, ir_v2_artifact.id)
                logger.info(f"Completed rendering processing directly for job {job_id}")
            except Exception as direct_error:
                logger.error(
                    f"Direct rendering processing failed for job {job_id}: {direct_error}",
                    exc_info=True,
                )
                # Update job status to indicate rendering failed
                await job_service.update_job_status(
                    job_id, JobStatus.FAILED, error_message=f"Failed to process rendering: {str(direct_error)}"
                )

            return {
                "success": True,
                "job_id": str(job_id),
                "ir_v2_artifact_id": str(ir_v2_artifact.id),
                "fingering_coverage": ir_v2_data.get("fingering_metadata", {}).get(
                    "coverage", 0.0
                ),
            }

    except Exception as e:
        logger.error(
            f"Fingering processing failed for job {job_id}: {e}", exc_info=True
        )

        async with AsyncSessionLocal() as db:
            job_service = JobService(db)
            await job_service.update_job_status(
                job_id, JobStatus.FINGERING_FAILED, error_message=str(e)
            )

        raise


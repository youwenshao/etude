"""Celery tasks for rendering processing."""

import asyncio
import logging
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.core.state_machine import JobStatus
from app.db.session import AsyncSessionLocal
from app.models.artifact import ArtifactType
from app.services.artifact_service import ArtifactService
from app.services.job_service import JobService
from app.services.ir_service import IRService
from app.services.storage_service import storage_service
from app.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.process_rendering", bind=True)
def process_rendering_task(self, job_id: str, ir_v2_artifact_id: str):
    """
    Celery task to render IR v2 to all output formats.

    Args:
        job_id: UUID of the job
        ir_v2_artifact_id: UUID of the IR v2 artifact
    """
    return asyncio.run(process_rendering_async(UUID(job_id), UUID(ir_v2_artifact_id)))


async def process_rendering_async(job_id: UUID, ir_v2_artifact_id: UUID):
    """Async implementation of rendering."""
    logger.info(f"Starting rendering for job {job_id}")

    try:
        async with AsyncSessionLocal() as db:
            # Initialize services
            job_service = JobService(db)
            artifact_service = ArtifactService(db)
            ir_service = IRService(db)

            # Update job status
            await job_service.update_job_status(job_id, JobStatus.RENDERING_PROCESSING)

            # Load IR v2
            ir_v2_artifact, ir_v2 = await ir_service.load_ir(ir_v2_artifact_id)

            logger.info(f"Loaded IR v2: {len(ir_v2.notes)} notes")

            # Call renderer service
            renderer_service_url = settings.RENDERER_SERVICE_URL

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{renderer_service_url}/render",
                    json={
                        "ir_v2": ir_v2.model_dump(),
                        "formats": ["musicxml", "midi", "svg"],
                    },
                )

                if response.status_code != 200:
                    raise Exception(f"Renderer service error: {response.text}")

                render_response = response.json()

            logger.info("Renderer service processing complete")

            # Store rendered artifacts
            formats = render_response["formats"]
            artifact_ids = {}

            # MusicXML
            if "musicxml" in formats:
                musicxml_data = formats["musicxml"].encode("utf-8")
                musicxml_artifact = await artifact_service.store_artifact(
                    job_id=job_id,
                    artifact_type=ArtifactType.MUSICXML.value,
                    data=musicxml_data,
                    metadata={"format": "musicxml", "source_ir_version": ir_v2.version},
                    parent_artifact_id=ir_v2_artifact_id,
                )
                artifact_ids["musicxml"] = str(musicxml_artifact.id)

            # MIDI
            if "midi" in formats:
                import base64

                midi_data = base64.b64decode(formats["midi"])
                midi_artifact = await artifact_service.store_artifact(
                    job_id=job_id,
                    artifact_type=ArtifactType.MIDI.value,
                    data=midi_data,
                    metadata={"format": "midi", "source_ir_version": ir_v2.version},
                    parent_artifact_id=ir_v2_artifact_id,
                )
                artifact_ids["midi"] = str(midi_artifact.id)

            # SVG
            if "svg" in formats:
                # Store each page separately
                svg_artifact_ids = []
                for i, svg_page in enumerate(formats["svg"]):
                    svg_data = svg_page.encode("utf-8")
                    svg_artifact = await artifact_service.store_artifact(
                        job_id=job_id,
                        artifact_type=ArtifactType.SVG.value,
                        data=svg_data,
                        metadata={
                            "format": "svg",
                            "page_number": i + 1,
                            "source_ir_version": ir_v2.version,
                        },
                        parent_artifact_id=ir_v2_artifact_id,
                    )
                    svg_artifact_ids.append(str(svg_artifact.id))
                artifact_ids["svg"] = svg_artifact_ids

            logger.info(f"Stored rendered artifacts: {list(artifact_ids.keys())}")

            # Update job status
            await job_service.update_job_status(job_id, JobStatus.COMPLETED)

            return {
                "success": True,
                "job_id": str(job_id),
                "artifact_ids": artifact_ids,
            }

    except Exception as e:
        logger.error(f"Rendering failed for job {job_id}: {e}", exc_info=True)

        async with AsyncSessionLocal() as db:
            job_service = JobService(db)
            await job_service.update_job_status(
                job_id, JobStatus.FAILED, error_message=str(e)
            )

        raise


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
    logger.info(
        f"Job {job_id}: Starting rendering for IR v2 artifact {ir_v2_artifact_id}",
        extra={"job_id": str(job_id), "ir_v2_artifact_id": str(ir_v2_artifact_id)}
    )

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

            logger.info(
                f"Job {job_id}: Loaded IR v2: version={ir_v2.version}, "
                f"notes={len(ir_v2.notes)}, staves={len(ir_v2.staves)}",
                extra={
                    "job_id": str(job_id),
                    "ir_version": ir_v2.version,
                    "note_count": len(ir_v2.notes),
                    "staff_count": len(ir_v2.staves),
                }
            )

            # Call renderer service
            renderer_service_url = settings.RENDERER_SERVICE_URL
            
            # Health check with retry logic
            health_check_passed = False
            max_health_retries = 3
            for retry in range(max_health_retries):
                try:
                    async with httpx.AsyncClient(timeout=5.0) as health_client:
                        health_response = await health_client.get(f"{renderer_service_url}/health")
                        if health_response.status_code == 200:
                            health_check_passed = True
                            logger.info(f"Job {job_id}: Renderer service health check passed")
                            break
                        else:
                            logger.warning(
                                f"Job {job_id}: Renderer service health check failed: "
                                f"{health_response.status_code} (attempt {retry + 1}/{max_health_retries})"
                            )
                except httpx.TimeoutException:
                    logger.warning(
                        f"Job {job_id}: Renderer service health check timeout (attempt {retry + 1}/{max_health_retries})"
                    )
                except httpx.ConnectError as e:
                    logger.warning(
                        f"Job {job_id}: Renderer service connection error: {e} "
                        f"(attempt {retry + 1}/{max_health_retries})"
                    )
                except Exception as health_error:
                    logger.warning(
                        f"Job {job_id}: Renderer service health check error: {health_error} "
                        f"(attempt {retry + 1}/{max_health_retries})"
                    )
                
                if retry < max_health_retries - 1:
                    await asyncio.sleep(1)  # Wait before retry
            
            if not health_check_passed:
                logger.warning(f"Job {job_id}: Renderer service health check failed after {max_health_retries} attempts, proceeding anyway")

            # Send request with job_id in headers for correlation
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Send ir_v2 as JSON body and formats as query parameter
                ir_v2_dict = ir_v2.model_dump(mode='json')
                logger.info(
                    f"Job {job_id}: Sending IR v2 to renderer: version={ir_v2_dict.get('version')}, "
                    f"notes={len(ir_v2_dict.get('notes', []))}, "
                    f"staves={len(ir_v2_dict.get('staves', []))}",
                    extra={
                        "job_id": str(job_id),
                        "ir_version": ir_v2_dict.get('version'),
                        "note_count": len(ir_v2_dict.get('notes', [])),
                        "staff_count": len(ir_v2_dict.get('staves', [])),
                    }
                )
                
                try:
                    # Use list of tuples for query params to ensure proper serialization
                    # FastAPI expects multiple query params like: ?formats=musicxml&formats=midi&formats=svg&formats=png
                    response = await client.post(
                        f"{renderer_service_url}/render",
                        json=ir_v2_dict,
                        params=[("formats", "musicxml"), ("formats", "midi"), ("formats", "svg"), ("formats", "png")],
                        headers={"X-Job-Id": str(job_id)},
                    )
                except httpx.TimeoutException as e:
                    error_msg = f"Renderer service request timeout after 120s: {str(e)}"
                    logger.error(f"Job {job_id}: {error_msg}")
                    raise Exception(error_msg) from e
                except httpx.ConnectError as e:
                    error_msg = f"Renderer service connection error: {str(e)}"
                    logger.error(f"Job {job_id}: {error_msg}")
                    raise Exception(error_msg) from e
                except httpx.RequestError as e:
                    error_msg = f"Renderer service request error: {str(e)}"
                    logger.error(f"Job {job_id}: {error_msg}")
                    raise Exception(error_msg) from e

                # Log response details for debugging
                logger.info(
                    f"Job {job_id}: Renderer response: status={response.status_code}, "
                    f"content-type={response.headers.get('content-type')}, "
                    f"content-length={len(response.content) if response.content else 0}",
                    extra={
                        "job_id": str(job_id),
                        "response_status": response.status_code,
                        "content_type": response.headers.get('content-type'),
                    }
                )

                if response.status_code != 200:
                    # Enhanced error extraction
                    error_detail = _extract_error_detail(response, job_id)
                    
                    # Log full response for debugging
                    logger.error(
                        f"Job {job_id}: Renderer service returned error {response.status_code}: {error_detail}. "
                        f"Full response text (first 2000 chars): {response.text[:2000] if response.text else 'None'}. "
                        f"Response headers: {dict(response.headers)}",
                        extra={
                            "job_id": str(job_id),
                            "response_status": response.status_code,
                            "error_detail": error_detail,
                        }
                    )
                    raise Exception(f"Renderer service error ({response.status_code}): {error_detail}")

                try:
                    render_response = response.json()
                except Exception as json_error:
                    error_msg = f"Failed to parse renderer response as JSON: {json_error}. Response text (first 500 chars): {response.text[:500] if response.text else 'None'}"
                    logger.error(f"Job {job_id}: {error_msg}")
                    raise Exception(error_msg) from json_error

            logger.info(
                f"Job {job_id}: Renderer service processing complete",
                extra={"job_id": str(job_id)}
            )

            # Validate response structure
            if "formats" not in render_response:
                error_msg = "Renderer response missing 'formats' field"
                logger.error(f"Job {job_id}: {error_msg}")
                raise ValueError(error_msg)
            
            # Store rendered artifacts
            formats = render_response["formats"]
            if not isinstance(formats, dict):
                error_msg = f"Renderer response 'formats' must be a dict, got {type(formats)}"
                logger.error(f"Job {job_id}: {error_msg}")
                raise ValueError(error_msg)
            
            # Validate that requested formats are present in response
            # Note: PNG is optional (may not be available if cairosvg not installed)
            requested_formats = ["musicxml", "midi", "svg"]
            optional_formats = ["png"]
            missing_formats = [fmt for fmt in requested_formats if fmt not in formats]
            if missing_formats:
                error_msg = f"Renderer response missing requested formats: {missing_formats}. Received: {list(formats.keys())}"
                logger.error(f"Job {job_id}: {error_msg}")
                raise ValueError(error_msg)
            
            # Validate SVG format structure
            if "svg" in formats:
                if not isinstance(formats["svg"], list):
                    error_msg = f"Renderer response 'svg' must be a list, got {type(formats['svg'])}"
                    logger.error(f"Job {job_id}: {error_msg}")
                    raise ValueError(error_msg)
                if len(formats["svg"]) == 0:
                    error_msg = "Renderer response 'svg' list is empty"
                    logger.error(f"Job {job_id}: {error_msg}")
                    raise ValueError(error_msg)
            
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

            # PNG (base64 encoded from renderer)
            if "png" in formats:
                png_artifact_ids = []
                for i, png_base64 in enumerate(formats["png"]):
                    # Store PNG as base64 string (client will decode)
                    png_data = png_base64.encode("utf-8")
                    png_artifact = await artifact_service.store_artifact(
                        job_id=job_id,
                        artifact_type=ArtifactType.PNG.value,
                        data=png_data,
                        metadata={
                            "format": "png",
                            "encoding": "base64",
                            "page_number": i + 1,
                            "source_ir_version": ir_v2.version,
                        },
                        parent_artifact_id=ir_v2_artifact_id,
                    )
                    png_artifact_ids.append(str(png_artifact.id))
                artifact_ids["png"] = png_artifact_ids

            logger.info(
                f"Job {job_id}: Stored rendered artifacts: {list(artifact_ids.keys())}",
                extra={"job_id": str(job_id), "artifact_types": list(artifact_ids.keys())}
            )

            # Update job status
            await job_service.update_job_status(job_id, JobStatus.COMPLETED)

            return {
                "success": True,
                "job_id": str(job_id),
                "artifact_ids": artifact_ids,
            }

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        
        logger.error(
            f"Job {job_id}: Rendering failed: {error_type}: {error_message}",
            exc_info=True,
            extra={
                "job_id": str(job_id),
                "error_type": error_type,
                "error_message": error_message,
            }
        )

        # Update job status with retry logic for DB errors
        max_db_retries = 3
        db_update_success = False
        for retry in range(max_db_retries):
            try:
                async with AsyncSessionLocal() as db:
                    job_service = JobService(db)
                    # Truncate error message if too long (database field limit)
                    truncated_error = error_message[:1000] if len(error_message) > 1000 else error_message
                    await job_service.update_job_status(
                        job_id, JobStatus.FAILED, error_message=truncated_error
                    )
                    db_update_success = True
                    logger.info(f"Job {job_id}: Updated job status to FAILED")
                    break
            except Exception as db_error:
                logger.error(
                    f"Job {job_id}: Failed to update job status (attempt {retry + 1}/{max_db_retries}): {db_error}",
                    exc_info=True
                )
                if retry < max_db_retries - 1:
                    await asyncio.sleep(0.5)  # Brief wait before retry
        
        if not db_update_success:
            logger.critical(
                f"Job {job_id}: CRITICAL: Failed to update job status after {max_db_retries} attempts. "
                f"Job may be stuck in RENDERING_PROCESSING state."
            )

        raise


def _extract_error_detail(response: httpx.Response, job_id: str | UUID) -> str:
    """
    Extract detailed error message from renderer service response.
    
    Handles various response formats and provides fallbacks.
    """
    # Try to parse as JSON first
    try:
        error_json = response.json()
        if isinstance(error_json, dict):
            # Check for nested 'detail' structure (our enhanced error format)
            if "detail" in error_json:
                detail = error_json["detail"]
                
                # If detail is a dict with error info
                if isinstance(detail, dict):
                    # Extract error message from structured response
                    error_parts = []
                    if "error" in detail:
                        error_parts.append(str(detail["error"]))
                    elif "message" in detail:
                        error_parts.append(str(detail["message"]))
                    elif "error_type" in detail and "message" in detail:
                        error_parts.append(f"{detail['error_type']}: {detail['message']}")
                    
                    # Include error_type if available
                    if "error_type" in detail and detail["error_type"] not in str(error_parts):
                        error_parts.append(f"(Type: {detail['error_type']})")
                    
                    if error_parts:
                        return "; ".join(error_parts)
                    else:
                        return str(detail)
                
                # If detail is a list (validation errors)
                elif isinstance(detail, list):
                    return "; ".join([str(e) for e in detail])
                
                # If detail is a string
                elif isinstance(detail, str):
                    return detail
                
                # Fallback: stringify the detail
                else:
                    return str(detail)
            
            # Check for 'message' field
            elif "message" in error_json:
                return str(error_json["message"])
            
            # Check for 'error' field
            elif "error" in error_json:
                return str(error_json["error"])
            
            # Use the whole JSON as string
            else:
                return str(error_json)
        
        # If JSON is not a dict, stringify it
        else:
            return str(error_json)
    
    except Exception as json_error:
        # If response is not JSON, use the text as-is
        raw_text = response.text or ""
        if raw_text:
            # Try to extract useful info from HTML/text responses
            if len(raw_text) > 500:
                return f"Non-JSON error response (first 500 chars): {raw_text[:500]}"
            else:
                return f"Non-JSON error response: {raw_text}"
        else:
            return f"HTTP {response.status_code} error (could not parse response: {json_error})"


"""Artifact management endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.artifact import ArtifactResponse, ArtifactLineageResponse
from app.services.artifact_service import ArtifactService
from app.services.job_service import JobService
from app.dependencies import get_current_active_user

router = APIRouter()


@router.get("/{artifact_id}", response_model=ArtifactResponse, status_code=status.HTTP_200_OK)
async def get_artifact(
    artifact_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ArtifactResponse:
    """
    Get artifact metadata by ID.

    - **artifact_id**: Artifact UUID

    Returns 404 if artifact not found, 403 if user doesn't own the job.
    """
    artifact_service = ArtifactService(db)
    result = await artifact_service.get_artifact(artifact_id)

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    artifact, _ = result

    # Check ownership via job
    job_service = JobService(db)
    job = await job_service.get_job(artifact.job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this artifact"
        )

    return ArtifactResponse.model_validate(artifact)


@router.get("/{artifact_id}/download", status_code=status.HTTP_200_OK)
async def download_artifact(
    artifact_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """
    Download artifact data.

    - **artifact_id**: Artifact UUID

    Returns file content with appropriate content-type.
    """
    artifact_service = ArtifactService(db)
    result = await artifact_service.get_artifact(artifact_id)

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    artifact, data = result

    # Check ownership via job
    job_service = JobService(db)
    job = await job_service.get_job(artifact.job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this artifact"
        )

    # Determine content type
    content_type_map = {
        "pdf": "application/pdf",
        "ir_v1": "application/json",
        "ir_v2": "application/json",
        "musicxml": "application/xml",
        "midi": "audio/midi",
        "svg": "image/svg+xml",
    }
    content_type = content_type_map.get(artifact.artifact_type, "application/octet-stream")

    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{artifact.id}.{artifact.artifact_type}"'},
    )


@router.get("/{artifact_id}/lineage", response_model=ArtifactLineageResponse, status_code=status.HTTP_200_OK)
async def get_artifact_lineage(
    artifact_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ArtifactLineageResponse:
    """
    Get artifact lineage graph (ancestors and descendants).

    - **artifact_id**: Artifact UUID

    Returns lineage information showing transformation relationships.
    """
    artifact_service = ArtifactService(db)
    
    # Get artifact
    result = await artifact_service.get_artifact(artifact_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    artifact, _ = result

    # Check ownership via job
    job_service = JobService(db)
    job = await job_service.get_job(artifact.job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this artifact"
        )

    # Get lineage
    lineage = await artifact_service.get_artifact_lineage(artifact_id)

    return ArtifactLineageResponse(
        artifact=ArtifactResponse.model_validate(artifact),
        ancestors=[ArtifactResponse.model_validate(a) for a in lineage["ancestors"]],
        descendants=[ArtifactResponse.model_validate(d) for d in lineage["descendants"]],
    )


@router.get("/jobs/{job_id}/artifacts", response_model=list[ArtifactResponse], status_code=status.HTTP_200_OK)
async def list_job_artifacts(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ArtifactResponse]:
    """
    List all artifacts for a job.

    - **job_id**: Job UUID

    Returns 404 if job not found, 403 if user doesn't own the job.
    """
    job_service = JobService(db)
    job = await job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this job"
        )

    artifacts = await job_service.get_job_artifacts(job_id)
    return [ArtifactResponse.model_validate(artifact) for artifact in artifacts]


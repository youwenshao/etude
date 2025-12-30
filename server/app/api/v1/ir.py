"""IR management endpoints."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.symbolic_ir.v1.schema import SymbolicScoreIR
from app.services.ir_service import IRService
from app.services.job_service import JobService
from app.dependencies import get_current_active_user, get_ir_service

router = APIRouter()


@router.post("/validate", response_model=dict, status_code=status.HTTP_200_OK)
async def validate_ir(
    ir_data: dict,
    ir_service: Annotated[IRService, Depends(get_ir_service)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """
    Validate IR data against the schema without storing it.
    Useful for development and testing.

    - **ir_data**: IR data as dictionary

    Returns validation result with success status and any errors.
    """
    try:
        ir = await ir_service.validate_ir(ir_data)
        return {
            "valid": True,
            "version": ir.version,
            "schema_type": ir.schema_type,
            "note_count": len(ir.notes),
            "message": "IR data is valid",
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "message": "IR data validation failed",
        }


@router.get("/{artifact_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def get_ir_by_artifact_id(
    artifact_id: UUID,
    ir_service: Annotated[IRService, Depends(get_ir_service)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Get IR by artifact ID (deserialized).

    - **artifact_id**: Artifact UUID

    Returns 404 if artifact not found, 403 if user doesn't own the job.
    """
    try:
        artifact, ir = await ir_service.load_ir(artifact_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Check ownership via job
    job_service = JobService(db)
    job = await job_service.get_job(artifact.job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this artifact",
        )

    # Return IR as dict (Pydantic will serialize)
    return ir.model_dump(mode="json")


@router.post("/jobs/{job_id}", response_model=dict, status_code=status.HTTP_201_CREATED)
async def store_ir_for_job(
    job_id: UUID,
    ir_data: dict,
    ir_service: Annotated[IRService, Depends(get_ir_service)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    parent_artifact_id: Optional[UUID] = None,
) -> dict:
    """
    Store new IR for a job.

    - **job_id**: Job UUID
    - **ir_data**: IR data as dictionary
    - **parent_artifact_id**: Optional parent artifact ID for lineage

    Returns 404 if job not found, 403 if user doesn't own the job.
    """
    # Check job ownership
    job_service = JobService(db)
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this job",
        )

    # Validate IR data
    try:
        ir = await ir_service.validate_ir(ir_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid IR data: {str(e)}",
        )

    # Store IR
    artifact = await ir_service.store_ir(
        job_id=job_id,
        ir=ir,
        parent_artifact_id=parent_artifact_id,
    )

    return {
        "artifact_id": str(artifact.id),
        "version": ir.version,
        "note_count": len(ir.notes),
        "message": "IR stored successfully",
    }


@router.get("/jobs/{job_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def get_latest_ir_for_job(
    job_id: UUID,
    ir_service: Annotated[IRService, Depends(get_ir_service)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Get latest IR for a job.

    - **job_id**: Job UUID

    Returns 404 if job or IR not found, 403 if user doesn't own the job.
    """
    # Check job ownership
    job_service = JobService(db)
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this job",
        )

    # Get latest IR
    result = await ir_service.get_ir_by_job(job_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No IR found for this job",
        )

    artifact, ir = result

    # Return IR as dict (Pydantic will serialize)
    return ir.model_dump(mode="json")


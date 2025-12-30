"""Job management endpoints."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.job import JobCreate, JobResponse, JobListResponse
from app.services.job_service import JobService
from app.dependencies import get_current_active_user

router = APIRouter()


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(..., description="PDF file to process"),
) -> JobResponse:
    """
    Create a new job by uploading a PDF file.

    - **file**: PDF file to process (multipart/form-data)

    Returns created job with status PENDING.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a PDF"
        )

    # Read file content
    pdf_content = await file.read()
    if len(pdf_content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty"
        )

    # Create job and store PDF
    job_service = JobService(db)
    job = await job_service.create_job(
        user_id=current_user.id, pdf_file=pdf_content, filename=file.filename or "upload.pdf"
    )

    return JobResponse.model_validate(job)


@router.get("/{job_id}", response_model=JobResponse, status_code=status.HTTP_200_OK)
async def get_job(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    """
    Get job details by ID.

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

    return JobResponse.model_validate(job)


@router.get("", response_model=JobListResponse, status_code=status.HTTP_200_OK)
async def list_jobs(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Optional[str] = Query(None, description="Filter by status"),
    stage: Optional[str] = Query(None, description="Filter by stage"),
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
) -> JobListResponse:
    """
    List user's jobs with filtering and pagination.

    - **status**: Optional status filter
    - **stage**: Optional stage filter
    - **limit**: Page size (1-100)
    - **offset**: Page offset

    Returns paginated list of jobs.
    """
    job_service = JobService(db)
    jobs, total = await job_service.list_user_jobs(
        user_id=current_user.id, status=status, stage=stage, limit=limit, offset=offset
    )

    return JobListResponse(
        items=[JobResponse.model_validate(job) for job in jobs],
        total=total,
        page=offset // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a job and all its artifacts.

    - **job_id**: Job UUID

    Returns 404 if job not found, 403 if user doesn't own the job.
    """
    job_service = JobService(db)
    job = await job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this job"
        )

    await job_service.delete_job(job_id)


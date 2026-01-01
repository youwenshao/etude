"""Tests for API endpoints."""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.core.state_machine import JobStatus
from app.models.artifact import Artifact, ArtifactType
from app.models.job import Job, JobStage


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_detailed_health_check(client: AsyncClient):
    """Test detailed health check endpoint."""
    response = await client.get("/api/v1/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    assert "database" in data["components"]
    assert "redis" in data["components"]


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "password123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert "id" in data


@pytest.mark.asyncio
async def test_login(client: AsyncClient, test_user):
    """Test user login."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_user):
    """Test getting current user info."""
    token = create_access_token(data={"sub": str(test_user.id)})
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


# Jobs API Tests


@pytest.mark.asyncio
async def test_create_job(client: AsyncClient, db_session, test_user, test_pdf_bytes):
    """Test creating a job by uploading a PDF."""
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Create a file-like object
    file_content = test_pdf_bytes
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}

    # Mock storage service to avoid actual file operations
    with patch("app.services.job_service.storage_service.upload_file", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = "jobs/test/artifacts/test.pdf"
        response = await client.post(
            "/api/v1/jobs",
            headers=headers,
            files=files,
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == JobStatus.PENDING.value
        assert data["stage"] == JobStage.OMR.value
        assert data["user_id"] == str(test_user.id)
        # Background task is added but may execute asynchronously
        # Just verify the job was created successfully


@pytest.mark.asyncio
async def test_create_job_invalid_file_type(client: AsyncClient, test_user):
    """Test creating a job with invalid file type."""
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    files = {"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")}

    response = await client.post(
        "/api/v1/jobs",
        headers=headers,
        files=files,
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_job_empty_file(client: AsyncClient, test_user):
    """Test creating a job with empty file."""
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}

    response = await client.post(
        "/api/v1/jobs",
        headers=headers,
        files=files,
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_job(client: AsyncClient, db_session, test_user):
    """Test getting a job by ID."""
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Create a job
    job = Job(
        user_id=test_user.id,
        status=JobStatus.PENDING.value,
        stage=JobStage.OMR.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    response = await client.get(
        f"/api/v1/jobs/{job.id}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(job.id)
    assert data["status"] == JobStatus.PENDING.value


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient, test_user):
    """Test getting a non-existent job."""
    from uuid import uuid4

    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(
        f"/api/v1/jobs/{uuid4()}",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_job_unauthorized(client: AsyncClient, db_session, test_user):
    """Test getting a job owned by another user."""
    from app.models.user import User
    from app.core.security import get_password_hash

    # Create another user
    other_user = User(
        email="other@example.com",
        hashed_password=get_password_hash("password"),
        full_name="Other User",
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    # Create a job for other user
    job = Job(
        user_id=other_user.id,
        status=JobStatus.PENDING.value,
        stage=JobStage.OMR.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Try to access with test_user's token
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(
        f"/api/v1/jobs/{job.id}",
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient, db_session, test_user):
    """Test listing user's jobs."""
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Create multiple jobs
    for i in range(3):
        job = Job(
            user_id=test_user.id,
            status=JobStatus.PENDING.value,
            stage=JobStage.OMR.value,
            job_metadata={"filename": f"test{i}.pdf"},
        )
        db_session.add(job)
    await db_session.commit()

    response = await client.get(
        "/api/v1/jobs",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 3
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_list_jobs_with_filters(client: AsyncClient, db_session, test_user):
    """Test listing jobs with status and stage filters."""
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Create jobs with different statuses
    job1 = Job(
        user_id=test_user.id,
        status=JobStatus.PENDING.value,
        stage=JobStage.OMR.value,
        job_metadata={"filename": "test1.pdf"},
    )
    job2 = Job(
        user_id=test_user.id,
        status=JobStatus.OMR_COMPLETED.value,
        stage=JobStage.FINGERING.value,
        job_metadata={"filename": "test2.pdf"},
    )
    db_session.add(job1)
    db_session.add(job2)
    await db_session.commit()

    # Filter by status
    response = await client.get(
        "/api/v1/jobs",
        headers=headers,
        params={"status": JobStatus.PENDING.value},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(job["status"] == JobStatus.PENDING.value for job in data["items"])

    # Filter by stage
    response = await client.get(
        "/api/v1/jobs",
        headers=headers,
        params={"stage": JobStage.FINGERING.value},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(job["stage"] == JobStage.FINGERING.value for job in data["items"])


@pytest.mark.asyncio
async def test_list_jobs_pagination(client: AsyncClient, db_session, test_user):
    """Test listing jobs with pagination."""
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Create multiple jobs
    for i in range(5):
        job = Job(
            user_id=test_user.id,
            status=JobStatus.PENDING.value,
            stage=JobStage.OMR.value,
            job_metadata={"filename": f"test{i}.pdf"},
        )
        db_session.add(job)
    await db_session.commit()

    # Test pagination
    response = await client.get(
        "/api/v1/jobs",
        headers=headers,
        params={"limit": 2, "offset": 0},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["page_size"] == 2
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_delete_job(client: AsyncClient, db_session, test_user):
    """Test deleting a job."""
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Create a job
    job = Job(
        user_id=test_user.id,
        status=JobStatus.PENDING.value,
        stage=JobStage.OMR.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    job_id = job.id

    response = await client.delete(
        f"/api/v1/jobs/{job_id}",
        headers=headers,
    )
    assert response.status_code == 204

    # Verify job is deleted
    response = await client.get(
        f"/api/v1/jobs/{job_id}",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_job_unauthorized(client: AsyncClient, db_session, test_user):
    """Test deleting a job owned by another user."""
    from app.models.user import User
    from app.core.security import get_password_hash

    # Create another user
    other_user = User(
        email="other@example.com",
        hashed_password=get_password_hash("password"),
        full_name="Other User",
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    # Create a job for other user
    job = Job(
        user_id=other_user.id,
        status=JobStatus.PENDING.value,
        stage=JobStage.OMR.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Try to delete with test_user's token
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.delete(
        f"/api/v1/jobs/{job.id}",
        headers=headers,
    )
    assert response.status_code == 403


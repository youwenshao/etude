"""Tests for Artifacts API endpoints."""

import hashlib
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.core.state_machine import JobStatus
from app.models.artifact import Artifact, ArtifactType
from app.models.job import Job, JobStage


@pytest.mark.asyncio
async def test_get_artifact(client: AsyncClient, db_session, test_user):
    """Test getting artifact metadata by ID."""
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
    await db_session.flush()

    # Create an artifact
    artifact_data = b"test artifact data"
    checksum = hashlib.sha256(artifact_data).hexdigest()
    artifact = Artifact(
        job_id=job.id,
        artifact_type=ArtifactType.PDF.value,
        schema_version="1.0.0",
        storage_path=f"jobs/{job.id}/artifacts/test.pdf",
        file_size=len(artifact_data),
        checksum=checksum,
        artifact_metadata={"filename": "test.pdf"},
    )
    db_session.add(artifact)
    await db_session.commit()
    await db_session.refresh(artifact)

    # Mock storage service
    with patch("app.services.artifact_service.storage_service.download_file", new_callable=AsyncMock, return_value=artifact_data):
        response = await client.get(
            f"/api/v1/artifacts/{artifact.id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(artifact.id)
        assert data["artifact_type"] == ArtifactType.PDF.value
        assert data["job_id"] == str(job.id)


@pytest.mark.asyncio
async def test_get_artifact_not_found(client: AsyncClient, test_user):
    """Test getting a non-existent artifact."""
    from uuid import uuid4

    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(
        f"/api/v1/artifacts/{uuid4()}",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_artifact_unauthorized(client: AsyncClient, db_session, test_user):
    """Test getting an artifact owned by another user."""
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
    await db_session.flush()

    # Create an artifact
    artifact_data = b"test artifact data"
    checksum = hashlib.sha256(artifact_data).hexdigest()
    artifact = Artifact(
        job_id=job.id,
        artifact_type=ArtifactType.PDF.value,
        schema_version="1.0.0",
        storage_path=f"jobs/{job.id}/artifacts/test.pdf",
        file_size=len(artifact_data),
        checksum=checksum,
        artifact_metadata={"filename": "test.pdf"},
    )
    db_session.add(artifact)
    await db_session.commit()
    await db_session.refresh(artifact)

    # Try to access with test_user's token
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Mock storage service - authorization check happens after download
    # So we need to mock the download to succeed, then authorization will return 403
    with patch("app.services.artifact_service.storage_service.download_file", new_callable=AsyncMock, return_value=artifact_data):
        response = await client.get(
            f"/api/v1/artifacts/{artifact.id}",
            headers=headers,
        )
        # Should return 403 after checking authorization
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_download_artifact(client: AsyncClient, db_session, test_user):
    """Test downloading artifact data."""
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
    await db_session.flush()

    # Create an artifact
    artifact_data = b"test artifact data"
    checksum = hashlib.sha256(artifact_data).hexdigest()
    artifact = Artifact(
        job_id=job.id,
        artifact_type=ArtifactType.PDF.value,
        schema_version="1.0.0",
        storage_path=f"jobs/{job.id}/artifacts/test.pdf",
        file_size=len(artifact_data),
        checksum=checksum,
        artifact_metadata={"filename": "test.pdf"},
    )
    db_session.add(artifact)
    await db_session.commit()
    await db_session.refresh(artifact)

    # Mock storage service
    with patch("app.services.artifact_service.storage_service.download_file", new_callable=AsyncMock, return_value=artifact_data):
        response = await client.get(
            f"/api/v1/artifacts/{artifact.id}/download",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.content == artifact_data
        assert response.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_download_artifact_musicxml(client: AsyncClient, db_session, test_user):
    """Test downloading MusicXML artifact."""
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Create a job
    job = Job(
        user_id=test_user.id,
        status=JobStatus.COMPLETED.value,
        stage=JobStage.RENDERING.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.flush()

    # Create a MusicXML artifact
    musicxml_data = b'<?xml version="1.0" encoding="UTF-8"?><score-partwise version="4.0"></score-partwise>'
    checksum = hashlib.sha256(musicxml_data).hexdigest()
    artifact = Artifact(
        job_id=job.id,
        artifact_type=ArtifactType.MUSICXML.value,
        schema_version="1.0.0",
        storage_path=f"jobs/{job.id}/artifacts/test.musicxml",
        file_size=len(musicxml_data),
        checksum=checksum,
        artifact_metadata={"format": "musicxml"},
    )
    db_session.add(artifact)
    await db_session.commit()
    await db_session.refresh(artifact)

    # Mock storage service
    with patch("app.services.artifact_service.storage_service.download_file", new_callable=AsyncMock, return_value=musicxml_data):
        response = await client.get(
            f"/api/v1/artifacts/{artifact.id}/download",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.content == musicxml_data
        assert "musicxml" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_get_artifact_lineage(client: AsyncClient, db_session, test_user):
    """Test getting artifact lineage."""
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Create a job
    job = Job(
        user_id=test_user.id,
        status=JobStatus.COMPLETED.value,
        stage=JobStage.RENDERING.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.flush()

    # Create parent artifact (PDF)
    pdf_data = b"pdf content"
    pdf_checksum = hashlib.sha256(pdf_data).hexdigest()
    pdf_artifact = Artifact(
        job_id=job.id,
        artifact_type=ArtifactType.PDF.value,
        schema_version="1.0.0",
        storage_path=f"jobs/{job.id}/artifacts/test.pdf",
        file_size=len(pdf_data),
        checksum=pdf_checksum,
        artifact_metadata={"filename": "test.pdf"},
    )
    db_session.add(pdf_artifact)
    await db_session.flush()

    # Create child artifact (IR v1)
    ir_data = b"ir content"
    ir_checksum = hashlib.sha256(ir_data).hexdigest()
    ir_artifact = Artifact(
        job_id=job.id,
        artifact_type=ArtifactType.IR_V1.value,
        schema_version="1.0.0",
        storage_path=f"jobs/{job.id}/artifacts/test_ir.json",
        file_size=len(ir_data),
        checksum=ir_checksum,
        parent_artifact_id=pdf_artifact.id,
        artifact_metadata={"version": "1.0.0"},
    )
    db_session.add(ir_artifact)
    await db_session.flush()  # Flush to get ir_artifact.id
    
    # Create lineage record (required for lineage queries)
    from app.models.artifact_lineage import ArtifactLineage
    lineage = ArtifactLineage(
        source_artifact_id=pdf_artifact.id,
        derived_artifact_id=ir_artifact.id,
        transformation_type=ArtifactType.IR_V1.value,
        transformation_version="1.0.0",
    )
    db_session.add(lineage)
    await db_session.commit()
    await db_session.refresh(ir_artifact)

    # Mock storage service
    with patch("app.services.artifact_service.storage_service.download_file", new_callable=AsyncMock, return_value=ir_data):
        response = await client.get(
            f"/api/v1/artifacts/{ir_artifact.id}/lineage",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["artifact"]["id"] == str(ir_artifact.id)
        assert len(data["ancestors"]) == 1
        assert data["ancestors"][0]["id"] == str(pdf_artifact.id)
        assert len(data["descendants"]) == 0


@pytest.mark.asyncio
async def test_list_job_artifacts(client: AsyncClient, db_session, test_user):
    """Test listing artifacts for a job."""
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Create a job
    job = Job(
        user_id=test_user.id,
        status=JobStatus.COMPLETED.value,
        stage=JobStage.RENDERING.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.flush()

    # Create multiple artifacts
    artifacts_data = [
        (b"pdf content", ArtifactType.PDF.value),
        (b"ir content", ArtifactType.IR_V1.value),
        (b"musicxml content", ArtifactType.MUSICXML.value),
    ]

    for i, (data, artifact_type) in enumerate(artifacts_data):
        checksum = hashlib.sha256(data).hexdigest()
        artifact = Artifact(
            job_id=job.id,
            artifact_type=artifact_type,
            schema_version="1.0.0",
            storage_path=f"jobs/{job.id}/artifacts/test_{i}",
            file_size=len(data),
            checksum=checksum,
            artifact_metadata={"index": i},
        )
        db_session.add(artifact)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/artifacts/jobs/{job.id}/artifacts",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    artifact_types = {a["artifact_type"] for a in data}
    assert ArtifactType.PDF.value in artifact_types
    assert ArtifactType.IR_V1.value in artifact_types
    assert ArtifactType.MUSICXML.value in artifact_types


@pytest.mark.asyncio
async def test_list_job_artifacts_not_found(client: AsyncClient, test_user):
    """Test listing artifacts for a non-existent job."""
    from uuid import uuid4

    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(
        f"/api/v1/artifacts/jobs/{uuid4()}/artifacts",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_job_artifacts_unauthorized(client: AsyncClient, db_session, test_user):
    """Test listing artifacts for a job owned by another user."""
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
        f"/api/v1/artifacts/jobs/{job.id}/artifacts",
        headers=headers,
    )
    assert response.status_code == 403


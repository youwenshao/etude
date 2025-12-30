"""Tests for database models."""

import pytest
from datetime import datetime
from uuid import uuid4

from app.models.user import User
from app.models.job import Job, JobStatus, JobStage
from app.models.artifact import Artifact, ArtifactType


@pytest.mark.asyncio
async def test_user_creation(db_session):
    """Test user model creation."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.is_active is True
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_job_creation(db_session, test_user):
    """Test job model creation."""
    job = Job(
        user_id=test_user.id,
        status=JobStatus.PENDING.value,
        stage=JobStage.OMR.value,
        job_metadata={"test": "data"},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    assert job.id is not None
    assert job.user_id == test_user.id
    assert job.status == JobStatus.PENDING.value
    assert job.stage == JobStage.OMR.value
    assert job.job_metadata == {"test": "data"}


@pytest.mark.asyncio
async def test_artifact_creation(db_session, test_user):
    """Test artifact model creation."""
    job = Job(
        user_id=test_user.id,
        status=JobStatus.PENDING.value,
        stage=JobStage.OMR.value,
    )
    db_session.add(job)
    await db_session.flush()

    artifact = Artifact(
        job_id=job.id,
        artifact_type=ArtifactType.PDF.value,
        schema_version="1.0.0",
        storage_path="test/path.pdf",
        file_size=1024,
        checksum="abc123",
        artifact_metadata={"test": "data"},
    )
    db_session.add(artifact)
    await db_session.commit()
    await db_session.refresh(artifact)

    assert artifact.id is not None
    assert artifact.job_id == job.id
    assert artifact.artifact_type == ArtifactType.PDF.value
    assert artifact.file_size == 1024


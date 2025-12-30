"""Tests for IR API endpoints."""

import pytest
from uuid import uuid4

from app.models.job import Job, JobStatus
from app.models.artifact import ArtifactType
from app.schemas.symbolic_ir.v1.schema import SymbolicScoreIR


@pytest.mark.asyncio
async def test_validate_ir_endpoint(client, test_user, minimal_ir_v1):
    """Test IR validation endpoint."""
    # Get auth token (simplified - in real test would use proper auth)
    from app.core.security import create_access_token
    
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test valid IR
    response = await client.post(
        "/api/v1/ir/validate",
        json=minimal_ir_v1,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["version"] == "1.0.0"
    
    # Test invalid IR
    invalid_ir = minimal_ir_v1.copy()
    del invalid_ir["metadata"]
    
    response = await client.post(
        "/api/v1/ir/validate",
        json=invalid_ir,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "error" in data


@pytest.mark.asyncio
async def test_store_ir_endpoint(client, db_session, test_user, minimal_ir_v1):
    """Test storing IR via API."""
    from app.core.security import create_access_token
    
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a job
    job = Job(
        user_id=test_user.id,
        status=JobStatus.PENDING.value,
    )
    db_session.add(job)
    await db_session.commit()
    
    # Store IR
    response = await client.post(
        f"/api/v1/ir/jobs/{job.id}",
        json=minimal_ir_v1,
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "artifact_id" in data
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_get_ir_by_artifact_id(client, db_session, test_user, minimal_ir_v1):
    """Test getting IR by artifact ID."""
    from app.core.security import create_access_token
    from app.services.ir_service import IRService
    
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a job and store IR
    job = Job(
        user_id=test_user.id,
        status=JobStatus.PENDING.value,
    )
    db_session.add(job)
    await db_session.flush()
    
    ir_service = IRService(db_session)
    ir = SymbolicScoreIR.model_validate(minimal_ir_v1)
    artifact = await ir_service.store_ir(job_id=job.id, ir=ir)
    await db_session.commit()
    
    # Get IR by artifact ID
    response = await client.get(
        f"/api/v1/ir/{artifact.id}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"
    assert len(data["notes"]) == 1


@pytest.mark.asyncio
async def test_get_latest_ir_for_job(client, db_session, test_user, minimal_ir_v1):
    """Test getting latest IR for a job."""
    from app.core.security import create_access_token
    from app.services.ir_service import IRService
    
    token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a job and store IR
    job = Job(
        user_id=test_user.id,
        status=JobStatus.PENDING.value,
    )
    db_session.add(job)
    await db_session.flush()
    
    ir_service = IRService(db_session)
    ir = SymbolicScoreIR.model_validate(minimal_ir_v1)
    await ir_service.store_ir(job_id=job.id, ir=ir)
    await db_session.commit()
    
    # Get latest IR for job
    response = await client.get(
        f"/api/v1/ir/jobs/{job.id}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"
    assert len(data["notes"]) == 1


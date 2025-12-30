"""Tests for IR service."""

import pytest
from uuid import uuid4

from app.models.job import Job, JobStatus
from app.models.artifact import ArtifactType
from app.schemas.symbolic_ir.v1.schema import SymbolicScoreIR
from app.services.ir_service import IRService


@pytest.mark.asyncio
async def test_store_ir(db_session, test_user, minimal_ir_v1):
    """Test storing an IR."""
    # Create a job
    job = Job(
        user_id=test_user.id,
        status=JobStatus.PENDING.value,
    )
    db_session.add(job)
    await db_session.flush()
    
    # Create IR service
    ir_service = IRService(db_session)
    
    # Validate and create IR
    ir = SymbolicScoreIR.model_validate(minimal_ir_v1)
    
    # Store IR
    artifact = await ir_service.store_ir(
        job_id=job.id,
        ir=ir,
    )
    
    assert artifact.job_id == job.id
    assert artifact.artifact_type == ArtifactType.IR_V1.value
    assert artifact.schema_version == "1.0.0"
    assert artifact.file_size > 0
    assert artifact.checksum is not None


@pytest.mark.asyncio
async def test_load_ir(db_session, test_user, minimal_ir_v1):
    """Test loading an IR."""
    # Create a job
    job = Job(
        user_id=test_user.id,
        status=JobStatus.PENDING.value,
    )
    db_session.add(job)
    await db_session.flush()
    
    # Create IR service
    ir_service = IRService(db_session)
    
    # Store IR
    ir = SymbolicScoreIR.model_validate(minimal_ir_v1)
    artifact = await ir_service.store_ir(job_id=job.id, ir=ir)
    
    # Load IR
    loaded_artifact, loaded_ir = await ir_service.load_ir(artifact.id)
    
    assert loaded_artifact.id == artifact.id
    assert loaded_ir.version == ir.version
    assert len(loaded_ir.notes) == len(ir.notes)
    assert loaded_ir.notes[0].note_id == ir.notes[0].note_id


@pytest.mark.asyncio
async def test_validate_ir(ir_service, minimal_ir_v1):
    """Test IR validation."""
    # Valid IR
    ir = await ir_service.validate_ir(minimal_ir_v1)
    assert isinstance(ir, SymbolicScoreIR)
    assert ir.version == "1.0.0"
    
    # Invalid IR (missing required field)
    invalid_ir = minimal_ir_v1.copy()
    del invalid_ir["metadata"]
    
    with pytest.raises(Exception):  # Should raise validation error
        await ir_service.validate_ir(invalid_ir)


@pytest.mark.asyncio
async def test_get_ir_by_job(db_session, test_user, minimal_ir_v1):
    """Test getting IR by job."""
    # Create a job
    job = Job(
        user_id=test_user.id,
        status=JobStatus.PENDING.value,
    )
    db_session.add(job)
    await db_session.flush()
    
    # Create IR service
    ir_service = IRService(db_session)
    
    # Store IR
    ir = SymbolicScoreIR.model_validate(minimal_ir_v1)
    await ir_service.store_ir(job_id=job.id, ir=ir)
    
    # Get IR by job
    result = await ir_service.get_ir_by_job(job.id)
    assert result is not None
    
    artifact, loaded_ir = result
    assert artifact.job_id == job.id
    assert loaded_ir.version == ir.version


@pytest.mark.asyncio
async def test_get_ir_by_job_not_found(db_session, test_user):
    """Test getting IR for job with no IR."""
    # Create a job
    job = Job(
        user_id=test_user.id,
        status=JobStatus.PENDING.value,
    )
    db_session.add(job)
    await db_session.flush()
    
    # Create IR service
    ir_service = IRService(db_session)
    
    # Get IR by job (should return None)
    result = await ir_service.get_ir_by_job(job.id)
    assert result is None


@pytest.mark.asyncio
async def test_store_ir_with_lineage(db_session, test_user, minimal_ir_v1):
    """Test storing IR with parent artifact lineage."""
    # Create a job
    job = Job(
        user_id=test_user.id,
        status=JobStatus.PENDING.value,
    )
    db_session.add(job)
    await db_session.flush()
    
    # Create parent artifact (PDF)
    from app.models.artifact import Artifact
    import hashlib
    
    parent_artifact = Artifact(
        job_id=job.id,
        artifact_type=ArtifactType.PDF.value,
        schema_version="1.0.0",
        storage_path="test.pdf",
        file_size=1000,
        checksum=hashlib.sha256(b"test").hexdigest(),
        artifact_metadata={},
    )
    db_session.add(parent_artifact)
    await db_session.flush()
    
    # Create IR service
    ir_service = IRService(db_session)
    
    # Store IR with parent
    ir = SymbolicScoreIR.model_validate(minimal_ir_v1)
    artifact = await ir_service.store_ir(
        job_id=job.id,
        ir=ir,
        parent_artifact_id=parent_artifact.id,
    )
    
    assert artifact.parent_artifact_id == parent_artifact.id
    
    # Check lineage was created
    from app.models.artifact_lineage import ArtifactLineage
    from sqlalchemy import select
    
    result = await db_session.execute(
        select(ArtifactLineage).where(
            ArtifactLineage.source_artifact_id == parent_artifact.id,
            ArtifactLineage.derived_artifact_id == artifact.id,
        )
    )
    lineage = result.scalar_one_or_none()
    assert lineage is not None
    assert lineage.transformation_type == "omr_to_ir"


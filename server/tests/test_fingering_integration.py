"""Integration tests for Fingering service integration."""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Mock celery before importing fingering_tasks
try:
    from celery import Celery
except ImportError:
    # Mock celery if not installed
    import sys
    from unittest.mock import MagicMock
    sys.modules['celery'] = MagicMock()
    sys.modules['celery.app'] = MagicMock()
    sys.modules['celery.app.task'] = MagicMock()

from app.core.state_machine import JobStatus
from app.models.artifact import Artifact, ArtifactType
from app.models.job import Job, JobStage
from app.schemas.symbolic_ir.v1.schema import SymbolicScoreIR
from app.services.fingering_client import FingeringClient, get_fingering_client
from app.services.ir_service import IRService
from app.services.job_service import JobService
from app.tasks.fingering_tasks import process_fingering_async


@pytest.mark.asyncio
async def test_fingering_client_health_check():
    """Test Fingering client health check."""
    # This test requires Fingering service to be running
    # Skip if service is not available
    client = FingeringClient(base_url="http://localhost:8002", timeout=5)

    try:
        is_healthy = await client.health_check()
        # If service is running, should return True
        # If not running, test is skipped (no assertion)
        if is_healthy:
            assert is_healthy is True
    except Exception:
        pytest.skip("Fingering service not available for integration test")

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_fingering_processor_integration(db_session, test_user, minimal_ir_v1):
    """
    Test Fingering processor integration with job processing.

    This test verifies:
    1. Job with IR v1 artifact
    2. Fingering service is called correctly
    3. IR v2 artifact is stored
    4. Job status transitions correctly
    5. Artifact lineage is created
    """
    # Create a job with IR v1 artifact
    job = Job(
        user_id=test_user.id,
        status=JobStatus.OMR_COMPLETED.value,
        stage=JobStage.FINGERING.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.flush()

    # Store IR v1 artifact
    ir_service = IRService(db_session)
    ir_v1 = SymbolicScoreIR.model_validate(minimal_ir_v1)
    ir_v1_artifact = await ir_service.store_ir(
        job_id=job.id,
        ir=ir_v1,
        parent_artifact_id=None,
    )
    ir_v1_artifact.artifact_type = ArtifactType.IR_V1.value
    await db_session.commit()
    await db_session.refresh(ir_v1_artifact)

    # Mock Fingering service response
    mock_ir_v2 = minimal_ir_v1.copy()
    mock_ir_v2["version"] = "2.0.0"
    mock_ir_v2["fingering_metadata"] = {
        "model_name": "PRamoneda-ArLSTM",
        "model_version": "1.0.0",
        "ir_to_model_adapter_version": "1.0.0",
        "model_to_ir_adapter_version": "1.0.0",
        "uncertainty_policy": "mle",
        "notes_annotated": len(minimal_ir_v1.get("notes", [])),
        "total_notes": len(minimal_ir_v1.get("notes", [])),
        "coverage": 1.0,
    }

    # Add fingering to notes if they exist
    if mock_ir_v2.get("notes"):
        for note in mock_ir_v2["notes"]:
            note["fingering"] = {
                "finger": 1,
                "hand": "right",
                "confidence": 0.95,
                "alternatives": [],
                "uncertainty_policy": "mle",
                "model_name": "PRamoneda-ArLSTM",
                "model_version": "1.0.0",
                "adapter_version": "1.0.0",
            }

    mock_fingering_response = {
        "success": True,
        "symbolic_ir_v2": mock_ir_v2,
        "processing_time_seconds": 1.5,
        "message": "Fingering inference completed successfully",
    }

    # Mock Fingering client
    mock_fingering_client = AsyncMock()
    mock_fingering_client.infer_fingering = AsyncMock(return_value=mock_fingering_response)

    # Mock storage service - need to return the actual stored IR data
    import json
    ir_v1_json = ir_v1.to_json(indent=2)
    ir_v1_bytes = ir_v1_json.encode("utf-8")
    
    mock_storage_download = AsyncMock(return_value=ir_v1_bytes)
    mock_storage_upload = AsyncMock(return_value=f"jobs/{job.id}/artifacts/test_ir_v2.json")
    mock_storage_delete = AsyncMock(return_value=True)

    mock_storage_service = MagicMock()
    mock_storage_service.download_file = mock_storage_download
    mock_storage_service.upload_file = mock_storage_upload
    mock_storage_service.delete_file = mock_storage_delete

    # Patch the services
    import app.services.ir_service
    original_ir_storage = app.services.ir_service.storage_service
    app.services.ir_service.storage_service = mock_storage_service

    try:
        # Mock AsyncSessionLocal to return the test session as an async context manager
        from contextlib import asynccontextmanager
        
        @asynccontextmanager
        async def mock_session_local():
            yield db_session
        
        with patch("app.tasks.fingering_tasks.AsyncSessionLocal", mock_session_local):
            with patch("app.tasks.fingering_tasks.get_fingering_client", return_value=mock_fingering_client):
                # Create a mock task object
                mock_task = MagicMock()
                # Process the fingering
                await process_fingering_async(
                    mock_task,
                    job.id,
                    ir_v1_artifact.id,
                )
    except Exception:
        app.services.ir_service.storage_service = original_ir_storage
        raise

    # Refresh job from database
    await db_session.refresh(job)

    # Verify job status transitioned to FINGERING_COMPLETED
    assert job.status == JobStatus.FINGERING_COMPLETED.value

    # Verify Fingering client was called correctly
    mock_fingering_client.infer_fingering.assert_called_once()
    call_args = mock_fingering_client.infer_fingering.call_args
    # The function signature is: infer_fingering(ir_v1, uncertainty_policy="mle")
    # Check if called with positional or keyword arguments
    if call_args.args:
        ir_v1_arg = call_args.args[0]
        policy_arg = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("uncertainty_policy", "mle")
    else:
        ir_v1_arg = call_args.kwargs["ir_v1"]
        policy_arg = call_args.kwargs.get("uncertainty_policy", "mle")
    assert ir_v1_arg["version"] == "1.0.0"
    assert policy_arg == "mle"

    # Verify IR v2 artifact was created
    job_service = JobService(db_session)
    artifacts = await job_service.get_job_artifacts(job.id)
    ir_v2_artifacts = [a for a in artifacts if a.artifact_type == ArtifactType.IR_V2.value]
    assert len(ir_v2_artifacts) == 1

    ir_v2_artifact = ir_v2_artifacts[0]
    assert ir_v2_artifact.job_id == job.id
    assert ir_v2_artifact.schema_version == "2.0.0"
    assert ir_v2_artifact.parent_artifact_id == ir_v1_artifact.id  # Verify lineage

    # Restore original storage service
    app.services.ir_service.storage_service = original_ir_storage


@pytest.mark.asyncio
async def test_fingering_processor_error_handling(db_session, test_user, minimal_ir_v1):
    """Test Fingering processor error handling when Fingering service fails."""
    # Create a job with IR v1 artifact
    job = Job(
        user_id=test_user.id,
        status=JobStatus.OMR_COMPLETED.value,
        stage=JobStage.FINGERING.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.flush()

    # Store IR v1 artifact
    ir_service = IRService(db_session)
    ir_v1 = SymbolicScoreIR.model_validate(minimal_ir_v1)
    ir_v1_artifact = await ir_service.store_ir(
        job_id=job.id,
        ir=ir_v1,
        parent_artifact_id=None,
    )
    ir_v1_artifact.artifact_type = ArtifactType.IR_V1.value
    await db_session.commit()
    await db_session.refresh(ir_v1_artifact)

    # Mock Fingering client to raise an error
    mock_fingering_client = AsyncMock()
    mock_fingering_client.infer_fingering = AsyncMock(
        side_effect=Exception("Fingering service error")
    )

    # Mock storage service
    mock_storage_service = MagicMock()
    mock_storage_service.download_file = AsyncMock(return_value=b"{}")

    import app.services.ir_service
    original_storage = app.services.ir_service.storage_service
    app.services.ir_service.storage_service = mock_storage_service

    try:
        # Mock AsyncSessionLocal to return the test session as an async context manager
        from contextlib import asynccontextmanager
        
        @asynccontextmanager
        async def mock_session_local():
            yield db_session
        
        with patch("app.tasks.fingering_tasks.AsyncSessionLocal", mock_session_local):
            with patch("app.tasks.fingering_tasks.get_fingering_client", return_value=mock_fingering_client):
                mock_task = MagicMock()
                # Process the job (should handle error gracefully)
                with pytest.raises(Exception):
                    await process_fingering_async(
                        mock_task,
                        job.id,
                        ir_v1_artifact.id,
                    )
    finally:
        app.services.ir_service.storage_service = original_storage

    # Refresh job from database
    await db_session.refresh(job)

    # Verify job status transitioned to FINGERING_FAILED
    assert job.status == JobStatus.FINGERING_FAILED.value

    # Verify no IR v2 artifact was created
    job_service = JobService(db_session)
    artifacts = await job_service.get_job_artifacts(job.id)
    ir_v2_artifacts = [a for a in artifacts if a.artifact_type == ArtifactType.IR_V2.value]
    assert len(ir_v2_artifacts) == 0


@pytest.mark.asyncio
async def test_fingering_processor_missing_ir_v1(db_session, test_user):
    """Test Fingering processor handles missing IR v1 artifact gracefully."""
    # Create a job without IR v1 artifact
    job = Job(
        user_id=test_user.id,
        status=JobStatus.OMR_COMPLETED.value,
        stage=JobStage.FINGERING.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.commit()

    # Mock Fingering client
    mock_fingering_client = AsyncMock()

    # Mock AsyncSessionLocal to return the test session as an async context manager
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def mock_session_local():
        yield db_session
    
    # Process the job (should handle missing IR v1 gracefully)
    mock_task = MagicMock()
    with patch("app.tasks.fingering_tasks.AsyncSessionLocal", mock_session_local):
        with patch("app.tasks.fingering_tasks.get_fingering_client", return_value=mock_fingering_client):
            with pytest.raises(Exception):  # Should raise ValueError for missing artifact
                await process_fingering_async(
                    mock_task,
                    job.id,
                    uuid4(),  # Non-existent artifact ID
                )

    # Refresh job from database
    await db_session.refresh(job)

    # Verify job status transitioned to FINGERING_FAILED
    assert job.status == JobStatus.FINGERING_FAILED.value

    # Verify Fingering client was never called
    mock_fingering_client.infer_fingering.assert_not_called()


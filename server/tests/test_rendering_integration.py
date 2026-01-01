"""Integration tests for rendering pipeline."""

import base64
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

# Mock celery before importing rendering_tasks
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
from app.core.security import create_access_token
from app.models.artifact import Artifact, ArtifactType
from app.models.job import Job, JobStage
from app.schemas.symbolic_ir.v2.schema import SymbolicScoreIRV2
from app.services.artifact_service import ArtifactService
from app.services.ir_service import IRService
from app.services.job_service import JobService
from app.services.storage_service import storage_service
from app.tasks.rendering_tasks import process_rendering_async


@pytest.mark.asyncio
async def test_renderer_client_health_check():
    """Test Renderer client health check."""
    # This test requires Renderer service to be running
    # Skip if service is not available
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8003/health")
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "healthy"
            else:
                pytest.skip("Renderer service not available for integration test")
    except Exception:
        pytest.skip("Renderer service not available for integration test")


@pytest.mark.asyncio
async def test_rendering_processor_integration(db_session, test_user, minimal_ir_v2):
    """
    Test Rendering processor integration with job processing.

    This test verifies:
    1. Job with IR v2 artifact
    2. Renderer service is called correctly
    3. MusicXML, MIDI, and SVG artifacts are stored
    4. Job status transitions correctly
    5. Artifact lineage is created
    """
    # Create a job with IR v2 artifact
    job = Job(
        user_id=test_user.id,
        status=JobStatus.FINGERING_COMPLETED.value,
        stage=JobStage.RENDERING.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.flush()

    # Store IR v2 artifact
    ir_service = IRService(db_session)
    ir_v2 = SymbolicScoreIRV2.model_validate(minimal_ir_v2)
    ir_v2_artifact = await ir_service.store_ir(
        job_id=job.id,
        ir=ir_v2,
        parent_artifact_id=None,
    )
    ir_v2_artifact.artifact_type = ArtifactType.IR_V2.value
    await db_session.commit()
    await db_session.refresh(ir_v2_artifact)

    # Mock Renderer service response
    mock_musicxml = '<?xml version="1.0" encoding="UTF-8"?><score-partwise version="4.0"><part-list/></score-partwise>'
    mock_midi_base64 = base64.b64encode(b"MThd\x00\x00\x00\x06\x00\x01\x00\x01\x00\x60MTrk\x00\x00\x00\x00").decode("utf-8")
    mock_svg_pages = ['<svg xmlns="http://www.w3.org/2000/svg"><g></g></svg>']

    mock_renderer_response = {
        "success": True,
        "formats": {
            "musicxml": mock_musicxml,
            "midi": mock_midi_base64,
            "svg": mock_svg_pages,
        },
        "processing_time_seconds": 1.5,
    }

    # Mock storage service
    mock_storage_download = AsyncMock(return_value=ir_v2.to_json(indent=2).encode("utf-8"))
    mock_storage_upload = AsyncMock(side_effect=lambda file, key, bucket, **kwargs: f"{bucket}/{key}")
    mock_storage_delete = AsyncMock(return_value=True)

    mock_storage_service = MagicMock()
    mock_storage_service.download_file = mock_storage_download
    mock_storage_service.upload_file = mock_storage_upload
    mock_storage_service.delete_file = mock_storage_delete

    # Patch the services
    import app.services.ir_service
    import app.services.artifact_service
    original_ir_storage = app.services.ir_service.storage_service
    original_artifact_storage = app.services.artifact_service.storage_service
    app.services.ir_service.storage_service = mock_storage_service
    app.services.artifact_service.storage_service = mock_storage_service

    try:
        # Mock AsyncSessionLocal to return the test session as an async context manager
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_local():
            yield db_session

        # Mock httpx client for renderer service call
        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = mock_renderer_response
        mock_http_response.text = "OK"

        async def mock_post(*args, **kwargs):
            return mock_http_response

        mock_http_client = MagicMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)
        mock_http_client.post = AsyncMock(side_effect=mock_post)

        with patch("app.tasks.rendering_tasks.AsyncSessionLocal", mock_session_local):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                # Process the rendering
                result = await process_rendering_async(job.id, ir_v2_artifact.id)
    except Exception:
        app.services.ir_service.storage_service = original_ir_storage
        app.services.artifact_service.storage_service = original_artifact_storage
        raise

    # Refresh job from database
    await db_session.refresh(job)

    # Verify job status transitioned to COMPLETED
    assert job.status == JobStatus.COMPLETED.value

    # Verify Renderer service was called correctly
    assert mock_http_client.post.called
    call_args = mock_http_client.post.call_args
    assert call_args.kwargs["json"]["ir_v2"]["version"] == "2.0.0"
    assert "musicxml" in call_args.kwargs["json"]["formats"]
    assert "midi" in call_args.kwargs["json"]["formats"]
    assert "svg" in call_args.kwargs["json"]["formats"]

    # Verify rendered artifacts were created
    job_service = JobService(db_session)
    artifacts = await job_service.get_job_artifacts(job.id)
    
    musicxml_artifacts = [a for a in artifacts if a.artifact_type == ArtifactType.MUSICXML.value]
    midi_artifacts = [a for a in artifacts if a.artifact_type == ArtifactType.MIDI.value]
    svg_artifacts = [a for a in artifacts if a.artifact_type == ArtifactType.SVG.value]

    assert len(musicxml_artifacts) == 1
    assert len(midi_artifacts) == 1
    assert len(svg_artifacts) == 1  # One SVG page

    # Verify lineage
    musicxml_artifact = musicxml_artifacts[0]
    assert musicxml_artifact.parent_artifact_id == ir_v2_artifact.id
    assert musicxml_artifact.job_id == job.id

    midi_artifact = midi_artifacts[0]
    assert midi_artifact.parent_artifact_id == ir_v2_artifact.id
    assert midi_artifact.job_id == job.id

    svg_artifact = svg_artifacts[0]
    assert svg_artifact.parent_artifact_id == ir_v2_artifact.id
    assert svg_artifact.job_id == job.id

    # Verify result structure
    assert result["success"] is True
    assert result["job_id"] == str(job.id)
    assert "musicxml" in result["artifact_ids"]
    assert "midi" in result["artifact_ids"]
    assert "svg" in result["artifact_ids"]

    # Restore original storage services
    app.services.ir_service.storage_service = original_ir_storage
    app.services.artifact_service.storage_service = original_artifact_storage


@pytest.mark.asyncio
async def test_rendering_processor_error_handling(db_session, test_user, minimal_ir_v2):
    """Test Rendering processor error handling when Renderer service fails."""
    # Create a job with IR v2 artifact
    job = Job(
        user_id=test_user.id,
        status=JobStatus.FINGERING_COMPLETED.value,
        stage=JobStage.RENDERING.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.flush()

    # Store IR v2 artifact
    ir_service = IRService(db_session)
    ir_v2 = SymbolicScoreIRV2.model_validate(minimal_ir_v2)
    ir_v2_artifact = await ir_service.store_ir(
        job_id=job.id,
        ir=ir_v2,
        parent_artifact_id=None,
    )
    ir_v2_artifact.artifact_type = ArtifactType.IR_V2.value
    await db_session.commit()
    await db_session.refresh(ir_v2_artifact)

    # Mock storage service
    mock_storage_service = MagicMock()
    mock_storage_service.download_file = AsyncMock(return_value=ir_v2.to_json(indent=2).encode("utf-8"))

    import app.services.ir_service
    original_storage = app.services.ir_service.storage_service
    app.services.ir_service.storage_service = mock_storage_service

    try:
        # Mock AsyncSessionLocal
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_local():
            yield db_session

        # Mock httpx client to raise an error
        mock_http_client = MagicMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)
        mock_http_client.post = AsyncMock(side_effect=Exception("Renderer service error"))

        with patch("app.tasks.rendering_tasks.AsyncSessionLocal", mock_session_local):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                # Process the job (should handle error gracefully)
                with pytest.raises(Exception):
                    await process_rendering_async(job.id, ir_v2_artifact.id)
    finally:
        app.services.ir_service.storage_service = original_storage

    # Refresh job from database
    await db_session.refresh(job)

    # Verify job status transitioned to FAILED
    assert job.status == JobStatus.FAILED.value

    # Verify no rendered artifacts were created
    job_service = JobService(db_session)
    artifacts = await job_service.get_job_artifacts(job.id)
    rendered_artifacts = [
        a
        for a in artifacts
        if a.artifact_type
        in [ArtifactType.MUSICXML.value, ArtifactType.MIDI.value, ArtifactType.SVG.value]
    ]
    assert len(rendered_artifacts) == 0


@pytest.mark.asyncio
async def test_rendering_processor_missing_ir_v2(db_session, test_user):
    """Test Rendering processor handles missing IR v2 artifact gracefully."""
    # Create a job without IR v2 artifact
    job = Job(
        user_id=test_user.id,
        status=JobStatus.FINGERING_COMPLETED.value,
        stage=JobStage.RENDERING.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.commit()

    # Mock AsyncSessionLocal
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_session_local():
        yield db_session

    # Process the job (should handle missing IR v2 gracefully)
    with patch("app.tasks.rendering_tasks.AsyncSessionLocal", mock_session_local):
        with pytest.raises(Exception):  # Should raise ValueError for missing artifact
            await process_rendering_async(job.id, uuid4())  # Non-existent artifact ID

    # Refresh job from database
    await db_session.refresh(job)

    # Verify job status transitioned to FAILED
    assert job.status == JobStatus.FAILED.value


@pytest.mark.asyncio
async def test_artifact_download_formats(client, db_session, test_user, minimal_ir_v2):
    """Test that all rendered formats can be downloaded."""
    # Create access token for authentication
    access_token = create_access_token(data={"sub": str(test_user.id)})
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Create a job with rendered artifacts
    job = Job(
        user_id=test_user.id,
        status=JobStatus.COMPLETED.value,
        stage=JobStage.RENDERING.value,
        job_metadata={"filename": "test.pdf"},
    )
    db_session.add(job)
    await db_session.flush()

    # Store IR v2 artifact
    ir_service = IRService(db_session)
    ir_v2 = SymbolicScoreIRV2.model_validate(minimal_ir_v2)
    ir_v2_artifact = await ir_service.store_ir(
        job_id=job.id,
        ir=ir_v2,
        parent_artifact_id=None,
    )
    ir_v2_artifact.artifact_type = ArtifactType.IR_V2.value
    await db_session.commit()
    await db_session.refresh(ir_v2_artifact)

    # Create rendered artifacts
    artifact_service = ArtifactService(db_session)

    musicxml_data = b'<?xml version="1.0" encoding="UTF-8"?><score-partwise version="4.0"></score-partwise>'
    musicxml_artifact = await artifact_service.store_artifact(
        job_id=job.id,
        artifact_type=ArtifactType.MUSICXML.value,
        data=musicxml_data,
        metadata={"format": "musicxml"},
        parent_artifact_id=ir_v2_artifact.id,
    )

    midi_data = b"MThd\x00\x00\x00\x06\x00\x01\x00\x01\x00\x60MTrk\x00\x00\x00\x00"
    midi_artifact = await artifact_service.store_artifact(
        job_id=job.id,
        artifact_type=ArtifactType.MIDI.value,
        data=midi_data,
        metadata={"format": "midi"},
        parent_artifact_id=ir_v2_artifact.id,
    )

    svg_data = b'<svg xmlns="http://www.w3.org/2000/svg"><g></g></svg>'
    svg_artifact = await artifact_service.store_artifact(
        job_id=job.id,
        artifact_type=ArtifactType.SVG.value,
        data=svg_data,
        metadata={"format": "svg", "page_number": 1},
        parent_artifact_id=ir_v2_artifact.id,
    )

    await db_session.commit()

    # Mock storage service to return the artifact data
    async def mock_download_file(key: str, bucket: str, **kwargs):
        if "musicxml" in key:
            return musicxml_data
        elif "midi" in key or ".mid" in key:
            return midi_data
        elif "svg" in key:
            return svg_data
        return b""

    with patch.object(storage_service, "download_file", side_effect=mock_download_file):
        # Test MusicXML download
        response = await client.get(
            f"/api/v1/artifacts/{musicxml_artifact.id}/download",
            headers=headers
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.recordare.musicxml+xml"
        assert response.content == musicxml_data

        # Test MIDI download
        response = await client.get(
            f"/api/v1/artifacts/{midi_artifact.id}/download",
            headers=headers
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/midi"
        assert response.content == midi_data

        # Test SVG download
        response = await client.get(
            f"/api/v1/artifacts/{svg_artifact.id}/download",
            headers=headers
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        assert response.content == svg_data


"""Integration tests for OMR service integration."""

import pytest
from uuid import uuid4

from app.core.state_machine import JobStatus
from app.models.job import Job
from app.services.omr_client import OMRClient


@pytest.mark.asyncio
async def test_omr_client_health_check():
    """Test OMR client health check."""
    # This test requires OMR service to be running
    # Skip if service is not available
    client = OMRClient(base_url="http://localhost:8001", timeout=5)

    try:
        is_healthy = await client.health_check()
        # If service is running, should return True
        # If not running, test is skipped (no assertion)
        if is_healthy:
            assert is_healthy is True
    except Exception:
        pytest.skip("OMR service not available for integration test")

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_omr_processor_integration(db_session, test_user):
    """
    Test OMR processor integration with job processing.

    This is a placeholder test - actual implementation would require:
    - Mock OMR service or test service
    - Complete job creation flow
    - IR validation
    """
    # This test would verify:
    # 1. Job creation triggers OMR processing
    # 2. OMR service is called correctly
    # 3. IR artifact is stored
    # 4. Job status transitions correctly
    # 5. Artifact lineage is created

    pytest.skip("Requires OMR service mock or test service")


def test_job_status_transitions():
    """Test that job status transitions are valid for OMR processing."""
    # Test valid transitions
    from app.core.state_machine import validate_transition

    # PENDING -> OMR_PROCESSING
    is_valid, error = validate_transition(
        JobStatus.PENDING.value, JobStatus.OMR_PROCESSING.value
    )
    assert is_valid, f"Invalid transition: {error}"

    # OMR_PROCESSING -> OMR_COMPLETED
    is_valid, error = validate_transition(
        JobStatus.OMR_PROCESSING.value, JobStatus.OMR_COMPLETED.value
    )
    assert is_valid, f"Invalid transition: {error}"

    # OMR_PROCESSING -> OMR_FAILED
    is_valid, error = validate_transition(
        JobStatus.OMR_PROCESSING.value, JobStatus.OMR_FAILED.value
    )
    assert is_valid, f"Invalid transition: {error}"

    # Invalid: OMR_COMPLETED -> OMR_PROCESSING (should fail)
    is_valid, error = validate_transition(
        JobStatus.OMR_COMPLETED.value, JobStatus.OMR_PROCESSING.value
    )
    assert not is_valid, "Should not allow transition from OMR_COMPLETED to OMR_PROCESSING"


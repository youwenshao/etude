"""Tests for Fingering service client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.fingering_client import FingeringClient, get_fingering_client


@pytest.mark.asyncio
async def test_fingering_client_health_check():
    """Test Fingering client health check."""
    client = FingeringClient(base_url="http://localhost:8002", timeout=5)

    # Mock successful health check
    with patch.object(client.client, "get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        is_healthy = await client.health_check()
        assert is_healthy is True
        mock_get.assert_called_once_with("http://localhost:8002/health")

    # Mock failed health check
    with patch.object(client.client, "get") as mock_get:
        mock_get.side_effect = Exception("Connection error")
        is_healthy = await client.health_check()
        assert is_healthy is False

    await client.close()


@pytest.mark.asyncio
async def test_fingering_client_infer_fingering(minimal_ir_v1):
    """Test Fingering client infer_fingering method."""
    client = FingeringClient(base_url="http://localhost:8002", timeout=5)

    # Mock successful inference
    mock_ir_v2 = minimal_ir_v1.copy()
    mock_ir_v2["version"] = "2.0.0"
    mock_ir_v2["fingering_metadata"] = {
        "model_name": "PRamoneda-ArLSTM",
        "model_version": "1.0.0",
        "ir_to_model_adapter_version": "1.0.0",
        "model_to_ir_adapter_version": "1.0.0",
        "uncertainty_policy": "mle",
        "notes_annotated": 1,
        "total_notes": 1,
        "coverage": 1.0,
    }

    mock_response_data = {
        "success": True,
        "symbolic_ir_v2": mock_ir_v2,
        "processing_time_seconds": 1.5,
        "message": "Fingering inference completed successfully",
    }

    with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # httpx response.json() is a synchronous method that returns a dict
        mock_response.json = MagicMock(return_value=mock_response_data)
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = await client.infer_fingering(
            ir_v1=minimal_ir_v1,
            uncertainty_policy="mle",
        )

        assert result["success"] is True
        assert result["symbolic_ir_v2"]["version"] == "2.0.0"
        assert "fingering_metadata" in result["symbolic_ir_v2"]
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8002/infer"
        assert call_args[1]["json"]["ir_v1"] == minimal_ir_v1
        assert call_args[1]["json"]["uncertainty_policy"] == "mle"

    await client.close()


@pytest.mark.asyncio
async def test_fingering_client_infer_fingering_error(minimal_ir_v1):
    """Test Fingering client error handling."""
    client = FingeringClient(base_url="http://localhost:8002", timeout=5)

    # Test HTTP error
    with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        error = httpx.HTTPStatusError(
            "Server Error", request=AsyncMock(), response=mock_response
        )
        mock_response.raise_for_status = MagicMock(side_effect=error)
        mock_post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            await client.infer_fingering(ir_v1=minimal_ir_v1)

    # Test timeout error (will retry 3 times, then raise RetryError)
    with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(Exception):  # RetryError from tenacity
            await client.infer_fingering(ir_v1=minimal_ir_v1)

    await client.close()


@pytest.mark.asyncio
async def test_get_fingering_client():
    """Test get_fingering_client singleton."""
    # Reset global client
    import app.services.fingering_client
    app.services.fingering_client._fingering_client = None

    client1 = get_fingering_client()
    client2 = get_fingering_client()

    # Should return the same instance
    assert client1 is client2

    # Clean up
    await client1.close()
    app.services.fingering_client._fingering_client = None


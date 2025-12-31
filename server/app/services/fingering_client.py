"""HTTP client for Fingering service."""

import logging
from typing import Any, Dict

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)


class FingeringClient:
    """HTTP client for communicating with Fingering service."""

    def __init__(self, base_url: str, timeout: int = 180):
        """
        Initialize Fingering client.

        Args:
            base_url: Base URL of Fingering service (e.g., "http://fingering-service:8002")
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def health_check(self) -> bool:
        """
        Check if Fingering service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Fingering service health check failed: {e}")
            return False

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def infer_fingering(
        self,
        ir_v1: Dict[str, Any],
        uncertainty_policy: str = "mle",
    ) -> Dict[str, Any]:
        """
        Infer fingering for Symbolic IR v1 and return IR v2.

        Args:
            ir_v1: Symbolic Score IR v1 as dictionary
            uncertainty_policy: Uncertainty handling policy ("mle" or "sampling")

        Returns:
            Dictionary containing IR v2 with fingering annotations

        Raises:
            httpx.HTTPError: If request fails
            ValueError: If response is invalid
        """
        logger.info(
            f"Calling Fingering service to infer fingering",
            ir_version=ir_v1.get("version", "unknown"),
            note_count=len(ir_v1.get("notes", [])),
            uncertainty_policy=uncertainty_policy,
        )

        try:
            # Prepare request payload
            payload = {
                "ir_v1": ir_v1,
                "uncertainty_policy": uncertainty_policy,
            }

            # Make request
            response = await self.client.post(
                f"{self.base_url}/infer",
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            logger.info(
                f"Fingering inference completed",
                processing_time=result.get("processing_time_seconds", 0),
                success=result.get("success", False),
            )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Fingering service returned error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.TimeoutException as e:
            logger.error(f"Fingering service request timed out: {e}")
            raise
        except httpx.NetworkError as e:
            logger.error(f"Fingering service network error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Fingering service: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global client instance
_fingering_client: FingeringClient | None = None


def get_fingering_client() -> FingeringClient:
    """Get the global Fingering client instance."""
    global _fingering_client

    if _fingering_client is None:
        fingering_url = getattr(settings, "FINGERING_SERVICE_URL", "http://fingering-service:8002")
        _fingering_client = FingeringClient(base_url=fingering_url, timeout=180)

    return _fingering_client


"""HTTP client for OMR service."""

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


class OMRClient:
    """HTTP client for communicating with OMR service."""

    def __init__(self, base_url: str, timeout: int = 300):
        """
        Initialize OMR client.

        Args:
            base_url: Base URL of OMR service (e.g., "http://omr:8001")
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def health_check(self) -> bool:
        """
        Check if OMR service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"OMR service health check failed: {e}")
            return False

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def process_pdf(
        self,
        pdf_bytes: bytes,
        source_pdf_artifact_id: str,
        filename: str | None = None,
    ) -> Dict[str, Any]:
        """
        Process PDF through OMR service and return Symbolic IR v1.

        Args:
            pdf_bytes: PDF file content as bytes
            source_pdf_artifact_id: Source PDF artifact ID for lineage
            filename: Optional original filename

        Returns:
            Dictionary containing IR data and processing metadata

        Raises:
            httpx.HTTPError: If request fails
            ValueError: If response is invalid
        """
        logger.info(
            f"Calling OMR service to process PDF",
            artifact_id=source_pdf_artifact_id,
            filename=filename,
        )

        try:
            # Prepare request payload as multipart form data
            files = {"pdf_bytes": ("document.pdf", pdf_bytes, "application/pdf")}
            data = {
                "source_pdf_artifact_id": source_pdf_artifact_id,
            }
            if filename:
                data["filename"] = filename

            # Make request
            response = await self.client.post(
                f"{self.base_url}/process",
                files=files,
                data=data,
            )
            response.raise_for_status()

            result = response.json()
            logger.info(
                f"OMR processing completed",
                pages=result.get("processing_metadata", {}).get("pages_processed", 0),
                notes=result.get("processing_metadata", {}).get("notes_detected", 0),
            )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"OMR service returned error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.TimeoutException as e:
            logger.error(f"OMR service request timed out: {e}")
            raise
        except httpx.NetworkError as e:
            logger.error(f"OMR service network error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling OMR service: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global client instance
_omr_client: OMRClient | None = None


def get_omr_client() -> OMRClient:
    """Get the global OMR client instance."""
    global _omr_client

    if _omr_client is None:
        omr_url = getattr(settings, "OMR_SERVICE_URL", "http://omr:8001")
        _omr_client = OMRClient(base_url=omr_url, timeout=300)

    return _omr_client


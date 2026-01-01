"""Response schemas for renderer service."""

from pydantic import BaseModel
from typing import Dict, Any, List, Union
import base64


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str


class RenderResponse(BaseModel):
    """Response from render endpoint."""

    success: bool
    formats: Dict[str, Union[str, bytes, List[str]]]
    processing_time_seconds: float
    message: str

    class Config:
        # Allow bytes in response
        arbitrary_types_allowed = True

    def model_dump(self, **kwargs):
        """Custom serialization to handle bytes."""
        data = super().model_dump(**kwargs)

        # Encode bytes as base64
        if "formats" in data:
            for format_name, content in data["formats"].items():
                if isinstance(content, bytes):
                    data["formats"][format_name] = base64.b64encode(content).decode(
                        "utf-8"
                    )

        return data


"""Response schemas for renderer service."""

from pydantic import BaseModel, field_serializer
from typing import Dict, Any, List, Union
import base64
import json


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

    def _convert_bytes_to_base64(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper method to convert bytes to base64 strings in formats dict."""
        if "formats" in data:
            for format_name, content in data["formats"].items():
                if isinstance(content, bytes):
                    data["formats"][format_name] = base64.b64encode(content).decode(
                        "utf-8"
                    )
                elif isinstance(content, list):
                    # Handle lists that might contain bytes (shouldn't happen, but be safe)
                    converted_list = []
                    for item in content:
                        if isinstance(item, bytes):
                            converted_list.append(base64.b64encode(item).decode("utf-8"))
                        else:
                            converted_list.append(item)
                    data["formats"][format_name] = converted_list
        return data

    def model_dump(self, **kwargs):
        """Custom serialization to handle bytes."""
        data = super().model_dump(**kwargs)
        return self._convert_bytes_to_base64(data)

    def model_dump_json(self, **kwargs) -> str:
        """Override to ensure bytes are converted before JSON serialization."""
        # First convert bytes to base64 using our custom dump
        data = self.model_dump(**kwargs)
        # Then serialize to JSON
        return json.dumps(data, **kwargs)

    @field_serializer("formats")
    def serialize_formats(self, value: Dict[str, Union[str, bytes, List[str]]]) -> Dict[str, Union[str, List[str]]]:
        """Serialize formats field, converting bytes to base64 strings."""
        serialized = {}
        for format_name, content in value.items():
            if isinstance(content, bytes):
                serialized[format_name] = base64.b64encode(content).decode("utf-8")
            elif isinstance(content, list):
                # Handle lists (e.g., SVG pages)
                serialized_list = []
                for item in content:
                    if isinstance(item, bytes):
                        serialized_list.append(base64.b64encode(item).decode("utf-8"))
                    else:
                        serialized_list.append(item)
                serialized[format_name] = serialized_list
            else:
                serialized[format_name] = content
        return serialized


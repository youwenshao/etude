"""Response schemas for fingering service API."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    model: str
    model_version: str
    model_type: str
    device: str
    model_status: Optional[str] = Field(
        default=None, description="Model loading status"
    )


class ServiceInfo(BaseModel):
    """Service metadata response."""

    service: str
    version: str
    model: Dict[str, str]
    capabilities: Dict[str, Any]


class FingeringResponse(BaseModel):
    """Response schema for fingering inference endpoint."""

    success: bool
    symbolic_ir_v2: Dict[str, Any] = Field(
        ..., description="Symbolic Score IR v2 with fingering annotations"
    )
    processing_time_seconds: float
    message: str


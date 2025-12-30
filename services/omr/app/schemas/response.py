"""Response schemas for OMR service API."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ServiceInfo(BaseModel):
    """Service metadata response."""

    service: str
    version: str
    model: Dict[str, str]
    capabilities: Dict[str, Any]


class OMRProcessResponse(BaseModel):
    """Response schema for OMR processing endpoint."""

    ir_data: Dict[str, Any] = Field(
        ..., description="Symbolic Score IR v1 as dictionary"
    )
    processing_metadata: Dict[str, Any] = Field(
        ..., description="Processing metadata (time, pages processed, etc.)"
    )
    confidence_summary: Dict[str, float] = Field(
        ..., description="Summary statistics of confidence scores"
    )


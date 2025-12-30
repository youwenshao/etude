"""Request schemas for OMR service API."""

from typing import Optional

from pydantic import BaseModel, Field


class OMRProcessRequest(BaseModel):
    """Request schema for OMR processing endpoint."""

    pdf_bytes: bytes = Field(..., description="PDF file content as bytes")
    source_pdf_artifact_id: Optional[str] = Field(
        default=None, description="Source PDF artifact ID for lineage tracking"
    )
    filename: Optional[str] = Field(
        default=None, description="Original PDF filename"
    )
    metadata: Optional[dict] = Field(
        default_factory=dict, description="Optional processing metadata"
    )


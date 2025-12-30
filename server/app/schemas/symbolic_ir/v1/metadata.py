"""Metadata models for the Symbolic Score IR."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GenerationMetadata(BaseModel):
    """Information about the service and model that generated this IR."""

    service: str = Field(..., description="Service name, e.g., 'omr-service'")
    model: str = Field(..., description="Model name, e.g., 'Polyphonic-TrOMR'")
    model_version: str = Field(..., description="Semantic version, e.g., '1.0.0'")

    timestamp: str = Field(..., description="ISO 8601 timestamp")
    processing_time_seconds: Optional[float] = Field(default=None, ge=0)

    # Configuration used during generation
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Model-specific configuration parameters",
    )


class LowConfidenceRegion(BaseModel):
    """Mark regions of the score with systematically low confidence."""

    start_measure: int
    end_measure: int
    average_confidence: float = Field(..., ge=0.0, le=1.0)
    reason: Optional[str] = Field(
        default=None,
        description="e.g., 'complex polyphony', 'unclear image quality'",
    )


class IRMetadata(BaseModel):
    """
    Complete provenance and metadata for the IR document.
    """

    # Musical metadata
    title: Optional[str] = None
    composer: Optional[str] = None
    opus: Optional[str] = None
    movement: Optional[str] = None
    copyright: Optional[str] = None

    # Source information
    source_pdf_artifact_id: str = Field(..., description="Reference to original PDF artifact")
    source_filename: Optional[str] = None

    # Generation metadata
    generated_by: GenerationMetadata

    # Score characteristics
    page_count: int = Field(..., ge=1)
    estimated_duration_seconds: Optional[float] = Field(default=None, ge=0)
    total_measures: Optional[int] = Field(default=None, ge=1)

    # Statistical summary (useful for quick analysis)
    note_count: int = Field(..., ge=0)
    chord_count: int = Field(..., ge=0)
    voice_count: int = Field(..., ge=1)

    # Quality indicators
    average_detection_confidence: float = Field(..., ge=0.0, le=1.0)
    low_confidence_regions: List[LowConfidenceRegion] = Field(default_factory=list)


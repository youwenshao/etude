"""Fingering annotation models for IR v2."""

from typing import List, Optional

from pydantic import BaseModel, Field


class FingeringAlternative(BaseModel):
    """Alternative fingering suggestion with confidence."""

    finger: int = Field(..., ge=0, le=6, description="0=none, 1-5=fingers, 6=thumb crossing")
    confidence: float = Field(..., ge=0.0, le=1.0)


class FingeringAnnotation(BaseModel):
    """
    Fingering annotation for a single note.
    Added by the fingering inference service.
    """

    finger: int = Field(
        ..., ge=0, le=6, description="0=none, 1-5=fingers, 6=thumb crossing"
    )
    hand: str = Field(..., description="'left' or 'right'")
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Alternative fingerings
    alternatives: List[FingeringAlternative] = Field(
        default_factory=list,
        description="Alternative fingering suggestions with confidence",
    )

    # Model metadata
    model_name: str = Field(..., description="e.g., 'PRamoneda-ArLSTM'")
    model_version: str = Field(..., description="Model version")
    adapter_version: str = Field(..., description="IR-to-Model adapter version")

    # Uncertainty policy used
    uncertainty_policy: str = Field(..., description="e.g., 'mle', 'sampling'")


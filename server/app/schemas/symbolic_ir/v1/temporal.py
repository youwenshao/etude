"""Temporal representation models for the Symbolic Score IR."""

from fractions import Fraction
from typing import Optional, Tuple

from pydantic import BaseModel, Field, field_serializer, field_validator


class TemporalPosition(BaseModel):
    """
    Dual time representation: both continuous and metric time.
    This is critical for bridging perception and symbolic reasoning.
    """

    # Continuous time (from audio/video alignment or OMR page position)
    onset_seconds: float = Field(..., ge=0, description="Absolute time in seconds")

    # Metric time (symbolic, quantized)
    measure: int = Field(..., ge=1, description="Measure number (1-indexed)")
    beat: float = Field(..., ge=0, description="Beat within measure (0-indexed)")

    # Beat position as rational number (for precise representation)
    beat_fraction: Fraction = Field(
        ...,
        description="Exact beat position as fraction (e.g., Fraction(5, 4) = 1.25 beats)",
    )

    # Absolute beat from start of piece
    absolute_beat: float = Field(..., ge=0)

    # Confidence in quantization (OMR may be uncertain about exact timing)
    quantization_confidence: float = Field(..., ge=0.0, le=1.0)

    @field_serializer("beat_fraction")
    def serialize_beat_fraction(self, value: Fraction) -> str:
        """Serialize Fraction as string (e.g., '5/4')."""
        return f"{value.numerator}/{value.denominator}"

    @field_validator("beat_fraction", mode="before")
    @classmethod
    def parse_beat_fraction(cls, value) -> Fraction:
        """Parse Fraction from string or tuple."""
        if isinstance(value, Fraction):
            return value
        if isinstance(value, str):
            # Parse "5/4" format
            parts = value.split("/")
            if len(parts) == 2:
                return Fraction(int(parts[0]), int(parts[1]))
            return Fraction(value)
        if isinstance(value, (list, tuple)) and len(value) == 2:
            # Parse [5, 4] format
            return Fraction(int(value[0]), int(value[1]))
        if isinstance(value, (int, float)):
            return Fraction(value)
        raise ValueError(f"Cannot parse Fraction from {value}")


class Duration(BaseModel):
    """
    Duration in both continuous and metric representations.
    """

    # Continuous duration
    duration_seconds: float = Field(..., ge=0)

    # Metric duration
    duration_beats: float = Field(..., ge=0)
    duration_fraction: Fraction = Field(..., description="Exact duration as fraction")

    # Notated duration type
    note_type: str = Field(
        ...,
        description="e.g., 'whole', 'half', 'quarter', 'eighth', '16th', '32nd'",
    )
    dots: int = Field(default=0, ge=0, le=3, description="Number of augmentation dots")

    # Tuplet information
    is_tuplet: bool = False
    tuplet_ratio: Optional[Tuple[int, int]] = Field(
        default=None,
        description="(actual_notes, normal_notes), e.g., (3, 2) for triplet",
    )

    @field_serializer("duration_fraction")
    def serialize_duration_fraction(self, value: Fraction) -> str:
        """Serialize Fraction as string (e.g., '5/4')."""
        return f"{value.numerator}/{value.denominator}"

    @field_validator("duration_fraction", mode="before")
    @classmethod
    def parse_duration_fraction(cls, value) -> Fraction:
        """Parse Fraction from string or tuple."""
        if isinstance(value, Fraction):
            return value
        if isinstance(value, str):
            # Parse "5/4" format
            parts = value.split("/")
            if len(parts) == 2:
                return Fraction(int(parts[0]), int(parts[1]))
            return Fraction(value)
        if isinstance(value, (list, tuple)) and len(value) == 2:
            # Parse [5, 4] format
            return Fraction(int(value[0]), int(value[1]))
        if isinstance(value, (int, float)):
            return Fraction(value)
        raise ValueError(f"Cannot parse Fraction from {value}")


"""Confidence and uncertainty models for the Symbolic Score IR."""

from pydantic import BaseModel, Field, model_validator


class NoteConfidence(BaseModel):
    """
    Multi-level confidence scores for different aspects of note detection.
    Allows downstream services to make informed decisions about uncertainty.
    """

    # Overall note detection confidence
    detection: float = Field(..., ge=0.0, le=1.0, description="Was a note detected here?")

    # Attribute-level confidences
    pitch: float = Field(..., ge=0.0, le=1.0)
    onset_time: float = Field(..., ge=0.0, le=1.0)
    duration: float = Field(..., ge=0.0, le=1.0)

    # Interpretation-level confidences
    voice: float = Field(..., ge=0.0, le=1.0)
    hand: float = Field(..., ge=0.0, le=1.0)
    chord_membership: float = Field(..., ge=0.0, le=1.0)

    # Overall confidence (aggregation of above)
    overall: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_overall_confidence(self) -> "NoteConfidence":
        """Ensure overall confidence is reasonable aggregate of components."""
        # Overall should not exceed max of components
        max_component = max(
            self.detection,
            self.pitch,
            self.onset_time,
            self.duration,
            self.voice,
            self.hand,
            self.chord_membership,
        )
        if self.overall > max_component:
            raise ValueError(
                "Overall confidence cannot exceed maximum component confidence"
            )
        return self


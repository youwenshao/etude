"""Spatial position models for the Symbolic Score IR."""

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box in page coordinates."""

    x: float
    y: float
    width: float
    height: float
    coordinate_system: str = Field(
        default="normalized",
        description="'pixels' or 'normalized' (0-1 range)",
    )


class SpatialPosition(BaseModel):
    """
    Staff-relative spatial position from OMR.
    Preserved for potential future use (e.g., correlating with original PDF).
    """

    # Staff assignment
    staff_id: str = Field(..., description="Reference to staff in staves array")

    # Vertical position on staff (staff-line relative)
    # Middle line of 5-line staff = 0, spaces and lines above/below
    staff_position: float = Field(
        ...,
        description="Vertical position relative to staff (0 = middle line)",
    )

    # Position on page (for multi-page scores)
    page_number: int = Field(..., ge=1)

    # Bounding box in page coordinates (pixels or normalized)
    bounding_box: BoundingBox

    # Confidence in staff assignment (OMR may be uncertain)
    staff_assignment_confidence: float = Field(..., ge=0.0, le=1.0)


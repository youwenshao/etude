"""Note event models for IR v2 with fingering annotations."""

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.symbolic_ir.v1.note import NoteEvent
from app.schemas.symbolic_ir.v2.fingering import FingeringAnnotation


class NoteEventV2(NoteEvent):
    """
    Extended note event with fingering annotation.
    Inherits all fields from IR v1 NoteEvent.
    """

    # NEW: Fingering annotation
    fingering: Optional[FingeringAnnotation] = Field(
        default=None,
        description="Fingering annotation added by fingering AI service",
    )


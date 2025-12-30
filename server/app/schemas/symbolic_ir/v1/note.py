"""Note event models for the Symbolic Score IR."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.symbolic_ir.v1.confidence import NoteConfidence
from app.schemas.symbolic_ir.v1.grouping import (
    ChordMembership,
    HandAssignment,
    VoiceAssignment,
)
from app.schemas.symbolic_ir.v1.spatial import SpatialPosition
from app.schemas.symbolic_ir.v1.temporal import Duration, TemporalPosition


class PitchRepresentation(BaseModel):
    """Multiple pitch representations for flexibility."""

    midi_note: int = Field(..., ge=0, le=127, description="MIDI note number (60 = C4)")

    # Symbolic representation
    pitch_class: str = Field(..., description="e.g., 'C', 'F#', 'Bb'")
    octave: int = Field(..., description="Octave number (C4 = middle C)")

    # Scientific pitch notation
    scientific_notation: str = Field(..., description="e.g., 'C4', 'F#5'")

    # Frequency (Hz) - useful for analysis
    frequency_hz: Optional[float] = Field(default=None, ge=0)

    # Accidental state (as notated, not sounding)
    accidental: Optional[str] = Field(
        default=None,
        description="'sharp', 'flat', 'natural', 'double-sharp', 'double-flat'",
    )


class NoteEvent(BaseModel):
    """
    Atomic musical note event with complete attributes.
    This is the fundamental unit of the IR.
    """

    # Unique identifier
    note_id: str = Field(..., description="Unique note identifier within this IR")

    # Pitch representation
    pitch: PitchRepresentation

    # Temporal information (dual representation)
    time: TemporalPosition
    duration: Duration

    # Spatial information (from OMR)
    spatial: SpatialPosition

    # Musical attributes
    articulation: Optional[List[str]] = Field(
        default=None,
        description="e.g., ['staccato', 'accent']",
    )
    dynamics: Optional[str] = Field(default=None, description="e.g., 'mf', 'pp'")

    # Grouping memberships (probabilistic)
    chord_membership: Optional[ChordMembership] = None
    voice_assignment: Optional[VoiceAssignment] = None
    hand_assignment: Optional[HandAssignment] = None

    # Notation-specific
    is_grace_note: bool = False
    is_tied_from_previous: bool = False
    is_tied_to_next: bool = False

    # Confidence scores
    confidence: NoteConfidence


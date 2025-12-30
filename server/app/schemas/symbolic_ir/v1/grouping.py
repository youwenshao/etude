"""Grouping and voice models for the Symbolic Score IR."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.symbolic_ir.v1.temporal import TemporalPosition


class ChordMembership(BaseModel):
    """
    Probabilistic chord membership.
    OMR may be uncertain whether simultaneous notes form a chord.
    """

    chord_id: str = Field(..., description="Unique chord identifier")
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Relative position in chord (root, third, fifth, etc.)
    chord_position: Optional[str] = Field(
        default=None,
        description="'root', 'third', 'fifth', 'seventh', etc.",
    )


class VoiceAlternative(BaseModel):
    """Alternative voice assignment with confidence."""

    voice_id: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class VoiceAssignment(BaseModel):
    """
    Probabilistic voice assignment within a staff.
    Critical for fingering inference and contrapuntal analysis.
    """

    voice_id: str = Field(..., description="Voice identifier (e.g., 'voice_0', 'voice_1')")
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Alternative voice assignments (OMR may suggest multiple possibilities)
    alternatives: List[VoiceAlternative] = Field(default_factory=list)


class HandAlternative(BaseModel):
    """Alternative hand assignment with confidence."""

    hand: str = Field(..., description="'left' or 'right'")
    confidence: float = Field(..., ge=0.0, le=1.0)


class HandAssignment(BaseModel):
    """
    Probabilistic hand assignment for piano music.
    Essential for fingering inference.
    """

    hand: str = Field(..., description="'left' or 'right'")
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Alternative hand assignments
    alternatives: List[HandAlternative] = Field(default_factory=list)


class ChordGroup(BaseModel):
    """
    Collection of simultaneous notes forming a chord.
    """

    chord_id: str
    note_ids: List[str] = Field(..., description="References to NoteEvent.note_id")

    # Temporal position (same for all notes in chord)
    time: TemporalPosition

    # Chord analysis (optional, can be added by future analysis layer)
    root: Optional[str] = None
    chord_type: Optional[str] = Field(default=None, description="e.g., 'major', 'minor7'")

    confidence: float = Field(..., ge=0.0, le=1.0, description="Chord grouping confidence")


class Voice(BaseModel):
    """Voice structure definition."""

    voice_id: str
    staff_id: str
    note_ids: List[str] = Field(..., description="Ordered list of note IDs in this voice")


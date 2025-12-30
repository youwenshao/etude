"""Symbolic Score IR v1.0.0 schema."""

from app.schemas.symbolic_ir.v1.schema import SymbolicScoreIR
from app.schemas.symbolic_ir.v1.note import NoteEvent, PitchRepresentation
from app.schemas.symbolic_ir.v1.temporal import TemporalPosition, Duration
from app.schemas.symbolic_ir.v1.spatial import SpatialPosition, BoundingBox
from app.schemas.symbolic_ir.v1.grouping import (
    ChordMembership,
    VoiceAssignment,
    HandAssignment,
    ChordGroup,
    Voice,
)
from app.schemas.symbolic_ir.v1.confidence import NoteConfidence
from app.schemas.symbolic_ir.v1.metadata import (
    IRMetadata,
    GenerationMetadata,
    LowConfidenceRegion,
)

__all__ = [
    "SymbolicScoreIR",
    "NoteEvent",
    "PitchRepresentation",
    "TemporalPosition",
    "Duration",
    "SpatialPosition",
    "BoundingBox",
    "ChordMembership",
    "VoiceAssignment",
    "HandAssignment",
    "ChordGroup",
    "Voice",
    "NoteConfidence",
    "IRMetadata",
    "GenerationMetadata",
    "LowConfidenceRegion",
]


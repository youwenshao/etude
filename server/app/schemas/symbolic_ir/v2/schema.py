"""Top-level Symbolic Score IR v2 schema with fingering annotations."""

from typing import Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from app.schemas.symbolic_ir.v1.grouping import ChordGroup, Voice
from app.schemas.symbolic_ir.v1.metadata import IRMetadata
from app.schemas.symbolic_ir.v1.schema import (
    KeySignature,
    Staff,
    Tempo,
    TimeSignature,
)
from app.schemas.symbolic_ir.v2.note import NoteEventV2


class FingeringMetadata(BaseModel):
    """Metadata about fingering inference process."""

    model_name: str
    model_version: str
    ir_to_model_adapter_version: str
    model_to_ir_adapter_version: str
    uncertainty_policy: str
    notes_annotated: int
    total_notes: int
    coverage: float = Field(..., ge=0.0, le=1.0, description="Fraction of notes with fingering")


class SymbolicScoreIRV2(BaseModel):
    """
    Symbolic Score IR v2: IR v1 + Fingering Annotations

    This is the output of the fingering inference stage.
    Extends IR v1 with optional fingering annotations on notes.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "2.0.0",
                "schema_type": "symbolic_score_ir",
                "metadata": {
                    "title": "Example Piece",
                    "composer": "Example Composer",
                    "source_pdf_artifact_id": "00000000-0000-0000-0000-000000000000",
                    "generated_by": {
                        "service": "fingering-service",
                        "model": "PRamoneda-ArLSTM",
                        "model_version": "1.0.0",
                        "timestamp": "2025-01-15T10:30:00Z",
                    },
                    "page_count": 1,
                    "note_count": 0,
                    "chord_count": 0,
                    "voice_count": 1,
                    "average_detection_confidence": 0.95,
                },
                "time_signature": {"numerator": 4, "denominator": 4, "changes": []},
                "key_signature": {"fifths": 0, "mode": "major"},
                "tempo": {"bpm": 120, "beat_unit": "quarter", "changes": []},
                "staves": [
                    {"staff_id": "staff_0", "clef": "treble", "part_name": "Piano Right Hand"}
                ],
                "notes": [],
                "chords": [],
                "voices": [],
                "fingering_metadata": {
                    "model_name": "PRamoneda-ArLSTM",
                    "model_version": "1.0.0",
                    "ir_to_model_adapter_version": "1.0.0",
                    "model_to_ir_adapter_version": "1.0.0",
                    "uncertainty_policy": "mle",
                    "notes_annotated": 0,
                    "total_notes": 0,
                    "coverage": 0.0,
                },
            }
        }
    )

    # Schema version
    version: str = Field(default="2.0.0", pattern=r"^\d+\.\d+\.\d+$")
    schema_type: Literal["symbolic_score_ir"] = "symbolic_score_ir"

    # Metadata
    metadata: IRMetadata

    # Global musical context
    time_signature: TimeSignature
    key_signature: KeySignature
    tempo: Tempo

    # Staff configuration
    staves: List[Staff]

    # Core musical content (with optional fingering annotations)
    notes: List[NoteEventV2] = Field(..., description="All note events in the score (may have fingering)")
    chords: List[ChordGroup] = Field(default_factory=list)
    voices: List[Voice] = Field(default_factory=list)

    # NEW: Fingering metadata
    fingering_metadata: FingeringMetadata = Field(
        ...,
        description="Metadata about fingering inference process",
    )

    # Derived indices (computed on load for efficient access)
    _note_by_id: Dict[str, NoteEventV2] = PrivateAttr(default_factory=dict)
    _notes_by_staff: Dict[str, List[NoteEventV2]] = PrivateAttr(default_factory=dict)
    _notes_by_time: List[NoteEventV2] = PrivateAttr(default_factory=list)

    def model_post_init(self, __context) -> None:
        """Build internal indices after model initialization."""
        self._build_indices()

    def _build_indices(self) -> None:
        """Build internal indices for efficient access."""
        # Index notes by ID
        self._note_by_id = {note.note_id: note for note in self.notes}

        # Group notes by staff
        self._notes_by_staff = {}
        for note in self.notes:
            staff_id = note.spatial.staff_id
            if staff_id not in self._notes_by_staff:
                self._notes_by_staff[staff_id] = []
            self._notes_by_staff[staff_id].append(note)

        # Sort notes by time
        self._notes_by_time = sorted(self.notes, key=lambda n: n.time.onset_seconds)

    # Accessor methods
    def get_note_by_id(self, note_id: str) -> NoteEventV2 | None:
        """Efficiently retrieve note by ID."""
        return self._note_by_id.get(note_id)

    def get_notes_by_staff(self, staff_id: str) -> List[NoteEventV2]:
        """Get all notes on a specific staff."""
        return self._notes_by_staff.get(staff_id, [])

    def get_notes_in_time_range(
        self, start_seconds: float, end_seconds: float
    ) -> List[NoteEventV2]:
        """Get all notes within a time range."""
        return [
            note for note in self._notes_by_time
            if start_seconds <= note.time.onset_seconds < end_seconds
        ]

    def get_notes_in_measure_range(
        self, start_measure: int, end_measure: int
    ) -> List[NoteEventV2]:
        """Get all notes within a measure range."""
        return [
            note for note in self.notes
            if start_measure <= note.time.measure <= end_measure
        ]

    def to_json(self, **kwargs) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(
            exclude={"_note_by_id", "_notes_by_staff", "_notes_by_time"}, **kwargs
        )

    @classmethod
    def from_json(cls, json_str: str) -> "SymbolicScoreIRV2":
        """Deserialize from JSON string."""
        return cls.model_validate_json(json_str)


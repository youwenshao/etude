"""Top-level Symbolic Score IR v1 schema."""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from app.schemas.symbolic_ir.v1.grouping import ChordGroup, Voice
from app.schemas.symbolic_ir.v1.metadata import IRMetadata
from app.schemas.symbolic_ir.v1.note import NoteEvent


class TimeSignatureChange(BaseModel):
    """Time signature change at a specific measure."""

    measure: int = Field(..., ge=1)
    numerator: int = Field(..., ge=1)
    denominator: int = Field(..., ge=1)


class TimeSignature(BaseModel):
    """Time signature with optional changes."""

    numerator: int = Field(..., ge=1)
    denominator: int = Field(..., ge=1)
    changes: List[TimeSignatureChange] = Field(default_factory=list)


class KeySignature(BaseModel):
    """Key signature representation."""

    fifths: int = Field(..., ge=-7, le=7, description="Number of sharps (positive) or flats (negative)")
    mode: str = Field(..., description="'major' or 'minor'")


class TempoChange(BaseModel):
    """Tempo change at a specific measure and beat."""

    measure: int = Field(..., ge=1)
    beat: float = Field(..., ge=0)
    bpm: float = Field(..., gt=0)


class Tempo(BaseModel):
    """Tempo with optional changes."""

    bpm: float = Field(..., gt=0, description="Beats per minute")
    beat_unit: str = Field(default="quarter", description="'whole', 'half', 'quarter', 'eighth'")
    changes: List[TempoChange] = Field(default_factory=list)


class Staff(BaseModel):
    """Staff configuration."""

    staff_id: str
    clef: str = Field(..., description="'treble', 'bass', 'alto', 'tenor'")
    part_name: Optional[str] = None


class SymbolicScoreIR(BaseModel):
    """
    Complete Symbolic Score Intermediate Representation v1.

    This is the core data structure for the entire Étude pipeline.
    All ML services operate on this representation.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "1.0.0",
                "schema_type": "symbolic_score_ir",
                "metadata": {
                    "title": "Example Piece",
                    "composer": "Example Composer",
                    "source_pdf_artifact_id": "00000000-0000-0000-0000-000000000000",
                    "generated_by": {
                        "service": "omr-service",
                        "model": "Polyphonic-TrOMR",
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
            }
        }
    )

    # Schema version
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    schema_type: Literal["symbolic_score_ir"] = "symbolic_score_ir"

    # Metadata
    metadata: IRMetadata

    # Global musical context
    time_signature: TimeSignature
    key_signature: KeySignature
    tempo: Tempo

    # Staff configuration
    staves: List[Staff]

    # Core musical content
    notes: List[NoteEvent] = Field(..., description="All note events in the score")
    chords: List[ChordGroup] = Field(default_factory=list)

    # Voice structure
    voices: List[Voice] = Field(default_factory=list)

    # Derived indices (computed on load for efficient access)
    _note_by_id: Dict[str, NoteEvent] = PrivateAttr(default_factory=dict)
    _notes_by_staff: Dict[str, List[NoteEvent]] = PrivateAttr(default_factory=dict)
    _notes_by_time: List[NoteEvent] = PrivateAttr(default_factory=list)

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
    def get_note_by_id(self, note_id: str) -> Optional[NoteEvent]:
        """Efficiently retrieve note by ID."""
        return self._note_by_id.get(note_id)

    def get_notes_by_staff(self, staff_id: str) -> List[NoteEvent]:
        """Get all notes on a specific staff."""
        return self._notes_by_staff.get(staff_id, [])

    def get_notes_in_time_range(
        self, start_seconds: float, end_seconds: float
    ) -> List[NoteEvent]:
        """Get all notes within a time range."""
        return [
            note for note in self._notes_by_time
            if start_seconds <= note.time.onset_seconds < end_seconds
        ]

    def get_notes_in_measure_range(
        self, start_measure: int, end_measure: int
    ) -> List[NoteEvent]:
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
    def from_json(cls, json_str: str) -> "SymbolicScoreIR":
        """Deserialize from JSON string."""
        return cls.model_validate_json(json_str)


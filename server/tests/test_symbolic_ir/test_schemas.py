"""Tests for IR schema validation."""

import pytest
from fractions import Fraction

from app.schemas.symbolic_ir.v1.schema import SymbolicScoreIR
from app.schemas.symbolic_ir.v1.note import NoteEvent, PitchRepresentation
from app.schemas.symbolic_ir.v1.temporal import TemporalPosition, Duration
from app.schemas.symbolic_ir.v1.spatial import SpatialPosition, BoundingBox
from app.schemas.symbolic_ir.v1.confidence import NoteConfidence
from app.schemas.symbolic_ir.v1.grouping import ChordMembership, VoiceAssignment, HandAssignment


def test_minimal_ir_validation(minimal_ir_v1):
    """Test that minimal IR fixture validates correctly."""
    ir = SymbolicScoreIR.model_validate(minimal_ir_v1)
    assert ir.version == "1.0.0"
    assert ir.schema_type == "symbolic_score_ir"
    assert len(ir.notes) == 1
    assert len(ir.staves) == 1


def test_realistic_ir_validation(realistic_ir_v1):
    """Test that realistic IR fixture validates correctly."""
    ir = SymbolicScoreIR.model_validate(realistic_ir_v1)
    assert ir.version == "1.0.0"
    assert ir.schema_type == "symbolic_score_ir"
    assert len(ir.notes) == 3
    assert len(ir.chords) == 1
    assert len(ir.voices) == 2


def test_fraction_serialization():
    """Test Fraction serialization and deserialization."""
    # Test TemporalPosition with Fraction
    temporal = TemporalPosition(
        onset_seconds=0.0,
        measure=1,
        beat=1.25,
        beat_fraction=Fraction(5, 4),
        absolute_beat=1.25,
        quantization_confidence=0.95,
    )
    
    # Serialize to dict
    data = temporal.model_dump()
    assert data["beat_fraction"] == "5/4"
    
    # Deserialize from dict
    temporal2 = TemporalPosition.model_validate(data)
    assert temporal2.beat_fraction == Fraction(5, 4)


def test_fraction_from_string():
    """Test Fraction parsing from string."""
    temporal = TemporalPosition(
        onset_seconds=0.0,
        measure=1,
        beat=1.25,
        beat_fraction="5/4",  # String format
        absolute_beat=1.25,
        quantization_confidence=0.95,
    )
    assert temporal.beat_fraction == Fraction(5, 4)


def test_fraction_from_tuple():
    """Test Fraction parsing from tuple."""
    temporal = TemporalPosition(
        onset_seconds=0.0,
        measure=1,
        beat=1.25,
        beat_fraction=[5, 4],  # Tuple format
        absolute_beat=1.25,
        quantization_confidence=0.95,
    )
    assert temporal.beat_fraction == Fraction(5, 4)


def test_note_confidence_validation():
    """Test NoteConfidence validation."""
    # Valid confidence
    confidence = NoteConfidence(
        detection=0.9,
        pitch=0.95,
        onset_time=0.9,
        duration=0.9,
        voice=0.85,
        hand=0.9,
        chord_membership=1.0,
        overall=0.9,  # Should not exceed max component (0.95)
    )
    assert confidence.overall == 0.9
    
    # Invalid: overall exceeds max component
    with pytest.raises(ValueError, match="Overall confidence cannot exceed"):
        NoteConfidence(
            detection=0.9,
            pitch=0.95,
            onset_time=0.9,
            duration=0.9,
            voice=0.85,
            hand=0.9,
            chord_membership=0.9,  # Lower max component
            overall=0.98,  # Exceeds max component (0.95)
        )


def test_ir_indices(minimal_ir_v1):
    """Test that IR builds indices correctly."""
    ir = SymbolicScoreIR.model_validate(minimal_ir_v1)
    
    # Test note lookup by ID
    note = ir.get_note_by_id("note_0")
    assert note is not None
    assert note.note_id == "note_0"
    
    # Test notes by staff
    notes = ir.get_notes_by_staff("staff_0")
    assert len(notes) == 1
    assert notes[0].note_id == "note_0"
    
    # Test time range query
    notes_in_range = ir.get_notes_in_time_range(0.0, 1.0)
    assert len(notes_in_range) == 1
    
    # Test measure range query
    notes_in_measure = ir.get_notes_in_measure_range(1, 1)
    assert len(notes_in_measure) == 1


def test_ir_json_serialization(minimal_ir_v1):
    """Test IR JSON serialization and deserialization."""
    ir = SymbolicScoreIR.model_validate(minimal_ir_v1)
    
    # Serialize to JSON
    json_str = ir.to_json()
    assert isinstance(json_str, str)
    assert "note_0" in json_str
    
    # Deserialize from JSON
    ir2 = SymbolicScoreIR.from_json(json_str)
    assert ir2.version == ir.version
    assert len(ir2.notes) == len(ir.notes)
    assert ir2.notes[0].note_id == ir.notes[0].note_id


def test_pitch_representation():
    """Test PitchRepresentation model."""
    pitch = PitchRepresentation(
        midi_note=60,
        pitch_class="C",
        octave=4,
        scientific_notation="C4",
        frequency_hz=261.63,
    )
    assert pitch.midi_note == 60
    assert pitch.pitch_class == "C"
    assert pitch.octave == 4


def test_chord_membership():
    """Test ChordMembership model."""
    membership = ChordMembership(
        chord_id="chord_0",
        confidence=0.95,
        chord_position="root",
    )
    assert membership.chord_id == "chord_0"
    assert membership.confidence == 0.95
    assert membership.chord_position == "root"


def test_voice_assignment():
    """Test VoiceAssignment model."""
    assignment = VoiceAssignment(
        voice_id="voice_0",
        confidence=0.9,
    )
    assert assignment.voice_id == "voice_0"
    assert assignment.confidence == 0.9
    assert len(assignment.alternatives) == 0


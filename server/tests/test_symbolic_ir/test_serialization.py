"""Tests for IR serialization and deserialization."""

import json
import pytest

from app.schemas.symbolic_ir.v1.schema import SymbolicScoreIR


def test_json_roundtrip(minimal_ir_v1):
    """Test that IR can be serialized and deserialized without data loss."""
    # Load original
    ir1 = SymbolicScoreIR.model_validate(minimal_ir_v1)
    
    # Serialize to JSON string
    json_str = ir1.to_json()
    
    # Deserialize from JSON string
    ir2 = SymbolicScoreIR.from_json(json_str)
    
    # Verify all fields match
    assert ir2.version == ir1.version
    assert ir2.schema_type == ir1.schema_type
    assert len(ir2.notes) == len(ir1.notes)
    assert ir2.notes[0].note_id == ir1.notes[0].note_id
    assert ir2.notes[0].pitch.midi_note == ir1.notes[0].pitch.midi_note


def test_json_indentation(minimal_ir_v1):
    """Test that JSON serialization respects indentation."""
    ir = SymbolicScoreIR.model_validate(minimal_ir_v1)
    
    # Serialize with indentation
    json_str = ir.to_json(indent=2)
    
    # Should contain newlines if indented
    assert "\n" in json_str
    
    # Should be valid JSON
    parsed = json.loads(json_str)
    assert parsed["version"] == "1.0.0"


def test_model_dump_json_excludes_private_attrs(minimal_ir_v1):
    """Test that private attributes are excluded from JSON."""
    ir = SymbolicScoreIR.model_validate(minimal_ir_v1)
    
    # Build indices (private attrs)
    assert hasattr(ir, "_note_by_id")
    assert len(ir._note_by_id) > 0
    
    # Serialize to JSON
    json_str = ir.to_json()
    json_data = json.loads(json_str)
    
    # Private attrs should not be in JSON
    assert "_note_by_id" not in json_data
    assert "_notes_by_staff" not in json_data
    assert "_notes_by_time" not in json_data


def test_fraction_serialization_in_json(minimal_ir_v1):
    """Test that Fraction objects serialize correctly in JSON."""
    ir = SymbolicScoreIR.model_validate(minimal_ir_v1)
    
    # Serialize to JSON
    json_str = ir.to_json()
    json_data = json.loads(json_str)
    
    # Check that beat_fraction is a string
    note_data = json_data["notes"][0]
    assert isinstance(note_data["time"]["beat_fraction"], str)
    assert "/" in note_data["time"]["beat_fraction"]  # Should be "0/1" format


def test_realistic_ir_serialization(realistic_ir_v1):
    """Test serialization of realistic IR with complex data."""
    ir = SymbolicScoreIR.model_validate(realistic_ir_v1)
    
    # Serialize and deserialize
    json_str = ir.to_json()
    ir2 = SymbolicScoreIR.from_json(json_str)
    
    # Verify complex structures
    assert len(ir2.chords) == len(ir.chords)
    assert len(ir2.voices) == len(ir.voices)
    assert ir2.metadata.low_confidence_regions[0].start_measure == 32


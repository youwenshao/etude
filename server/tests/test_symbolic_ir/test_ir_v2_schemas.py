"""Tests for IR v2 schema with fingering annotations."""

import pytest
from app.schemas.symbolic_ir.v2.schema import SymbolicScoreIRV2, FingeringMetadata
from app.schemas.symbolic_ir.v2.fingering import FingeringAnnotation, FingeringAlternative
from app.schemas.symbolic_ir.v2.note import NoteEventV2


def test_fingering_metadata_validation():
    """Test FingeringMetadata validation."""
    metadata = FingeringMetadata(
        model_name="PRamoneda-ArLSTM",
        model_version="1.0.0",
        ir_to_model_adapter_version="1.0.0",
        model_to_ir_adapter_version="1.0.0",
        uncertainty_policy="mle",
        notes_annotated=10,
        total_notes=10,
        coverage=1.0,
    )

    assert metadata.coverage == 1.0
    assert metadata.notes_annotated == 10


def test_fingering_metadata_coverage_bounds():
    """Test FingeringMetadata coverage bounds."""
    # Valid coverage
    metadata = FingeringMetadata(
        model_name="test",
        model_version="1.0.0",
        ir_to_model_adapter_version="1.0.0",
        model_to_ir_adapter_version="1.0.0",
        uncertainty_policy="mle",
        notes_annotated=5,
        total_notes=10,
        coverage=0.5,
    )
    assert metadata.coverage == 0.5

    # Coverage out of bounds should fail
    with pytest.raises(Exception):
        FingeringMetadata(
            model_name="test",
            model_version="1.0.0",
            ir_to_model_adapter_version="1.0.0",
            model_to_ir_adapter_version="1.0.0",
            uncertainty_policy="mle",
            notes_annotated=5,
            total_notes=10,
            coverage=1.5,  # Invalid: > 1.0
        )


def test_fingering_annotation_validation():
    """Test FingeringAnnotation validation."""
    annotation = FingeringAnnotation(
        finger=1,
        hand="right",
        confidence=0.95,
        alternatives=[
            FingeringAlternative(finger=2, confidence=0.05),
        ],
        uncertainty_policy="mle",
        model_name="PRamoneda-ArLSTM",
        model_version="1.0.0",
        adapter_version="1.0.0",
    )

    assert annotation.finger == 1
    assert annotation.hand == "right"
    assert annotation.confidence == 0.95
    assert len(annotation.alternatives) == 1
    assert annotation.model_name == "PRamoneda-ArLSTM"


def test_ir_v2_from_v1(minimal_ir_v1):
    """Test creating IR v2 from IR v1 data."""
    # Add fingering metadata and annotations
    ir_v2_data = minimal_ir_v1.copy()
    ir_v2_data["version"] = "2.0.0"
    ir_v2_data["fingering_metadata"] = {
        "model_name": "PRamoneda-ArLSTM",
        "model_version": "1.0.0",
        "ir_to_model_adapter_version": "1.0.0",
        "model_to_ir_adapter_version": "1.0.0",
        "uncertainty_policy": "mle",
        "notes_annotated": len(ir_v2_data.get("notes", [])),
        "total_notes": len(ir_v2_data.get("notes", [])),
        "coverage": 1.0,
    }

    # Add fingering to notes if they exist
    if ir_v2_data.get("notes"):
        for note in ir_v2_data["notes"]:
            note["fingering"] = {
                "finger": 1,
                "hand": "right",
                "confidence": 0.95,
                "alternatives": [],
                "uncertainty_policy": "mle",
                "model_name": "PRamoneda-ArLSTM",
                "model_version": "1.0.0",
                "adapter_version": "1.0.0",
            }

    ir_v2 = SymbolicScoreIRV2.model_validate(ir_v2_data)

    assert ir_v2.version == "2.0.0"
    assert ir_v2.fingering_metadata.model_name == "PRamoneda-ArLSTM"
    assert ir_v2.fingering_metadata.coverage == 1.0

    # Verify notes have fingering if they were added
    if ir_v2.notes:
        for note in ir_v2.notes:
            assert note.fingering is not None
            assert note.fingering.finger == 1
            assert note.fingering.hand == "right"


def test_ir_v2_serialization(minimal_ir_v1):
    """Test IR v2 JSON serialization."""
    ir_v2_data = minimal_ir_v1.copy()
    ir_v2_data["version"] = "2.0.0"
    ir_v2_data["fingering_metadata"] = {
        "model_name": "PRamoneda-ArLSTM",
        "model_version": "1.0.0",
        "ir_to_model_adapter_version": "1.0.0",
        "model_to_ir_adapter_version": "1.0.0",
        "uncertainty_policy": "mle",
        "notes_annotated": 0,
        "total_notes": len(ir_v2_data.get("notes", [])),
        "coverage": 0.0,
    }

    ir_v2 = SymbolicScoreIRV2.model_validate(ir_v2_data)

    # Serialize to JSON
    json_str = ir_v2.to_json()
    assert "2.0.0" in json_str
    assert "fingering_metadata" in json_str

    # Deserialize from JSON
    ir_v2_loaded = SymbolicScoreIRV2.from_json(json_str)
    assert ir_v2_loaded.version == "2.0.0"
    assert ir_v2_loaded.fingering_metadata.model_name == "PRamoneda-ArLSTM"


def test_ir_v2_indices(minimal_ir_v1):
    """Test IR v2 index building."""
    ir_v2_data = minimal_ir_v1.copy()
    ir_v2_data["version"] = "2.0.0"
    ir_v2_data["fingering_metadata"] = {
        "model_name": "test",
        "model_version": "1.0.0",
        "ir_to_model_adapter_version": "1.0.0",
        "model_to_ir_adapter_version": "1.0.0",
        "uncertainty_policy": "mle",
        "notes_annotated": 0,
        "total_notes": len(ir_v2_data.get("notes", [])),
        "coverage": 0.0,
    }

    ir_v2 = SymbolicScoreIRV2.model_validate(ir_v2_data)

    # Test index accessors
    if ir_v2.notes:
        note = ir_v2.notes[0]
        note_by_id = ir_v2.get_note_by_id(note.note_id)
        assert note_by_id is not None
        assert note_by_id.note_id == note.note_id

        notes_by_staff = ir_v2.get_notes_by_staff(note.spatial.staff_id)
        assert len(notes_by_staff) > 0


def test_ir_v2_optional_fingering(minimal_ir_v1):
    """Test that fingering is optional on notes."""
    ir_v2_data = minimal_ir_v1.copy()
    ir_v2_data["version"] = "2.0.0"
    ir_v2_data["fingering_metadata"] = {
        "model_name": "test",
        "model_version": "1.0.0",
        "ir_to_model_adapter_version": "1.0.0",
        "model_to_ir_adapter_version": "1.0.0",
        "uncertainty_policy": "mle",
        "notes_annotated": 0,
        "total_notes": len(ir_v2_data.get("notes", [])),
        "coverage": 0.0,
    }

    # Don't add fingering to notes - should still work
    ir_v2 = SymbolicScoreIRV2.model_validate(ir_v2_data)

    assert ir_v2.version == "2.0.0"
    if ir_v2.notes:
        # Fingering should be None if not provided
        for note in ir_v2.notes:
            assert note.fingering is None or isinstance(note.fingering, FingeringAnnotation)


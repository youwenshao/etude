"""Tests for IR-to-Model and Model-to-IR adapters."""

import pytest
import torch

from app.adapters.ir_to_model_adapter import IRToModelAdapter
from app.adapters.model_to_ir_adapter import ModelToIRAdapter


@pytest.fixture
def sample_ir_v1():
    """Create a minimal IR v1 for testing."""
    return {
        "version": "1.0.0",
        "schema_type": "symbolic_score_ir",
        "metadata": {
            "title": "Test Piece",
            "composer": "Test Composer",
            "source_pdf_artifact_id": "00000000-0000-0000-0000-000000000000",
            "generated_by": {
                "service": "omr-service",
                "model": "Polyphonic-TrOMR",
                "model_version": "1.0.0",
                "timestamp": "2025-01-15T10:30:00Z",
            },
            "page_count": 1,
            "note_count": 2,
            "chord_count": 0,
            "voice_count": 1,
            "average_detection_confidence": 0.9,
        },
        "time_signature": {"numerator": 4, "denominator": 4, "changes": []},
        "key_signature": {"fifths": 0, "mode": "major"},
        "tempo": {"bpm": 120, "beat_unit": "quarter", "changes": []},
        "staves": [
            {"staff_id": "staff_0", "clef": "treble"},
            {"staff_id": "staff_1", "clef": "bass"},
        ],
        "notes": [
            {
                "note_id": "note_1",
                "pitch": {
                    "midi_note": 60,
                    "pitch_class": "C",
                    "octave": 4,
                    "scientific_notation": "C4",
                },
                "time": {
                    "onset_seconds": 0.0,
                    "measure": 1,
                    "beat": 0.0,
                    "absolute_beat": 0.0,
                },
                "duration": {
                    "duration_seconds": 0.5,
                    "duration_beats": 0.5,
                    "note_type": "eighth",
                },
                "spatial": {"staff_id": "staff_0", "staff_position": 0.0, "page_number": 1},
                "hand_assignment": {"hand": "right", "confidence": 0.9, "alternatives": []},
                "confidence": {"overall": 0.9},
            },
            {
                "note_id": "note_2",
                "pitch": {
                    "midi_note": 48,
                    "pitch_class": "C",
                    "octave": 3,
                    "scientific_notation": "C3",
                },
                "time": {
                    "onset_seconds": 0.0,
                    "measure": 1,
                    "beat": 0.0,
                    "absolute_beat": 0.0,
                },
                "duration": {
                    "duration_seconds": 1.0,
                    "duration_beats": 1.0,
                    "note_type": "quarter",
                },
                "spatial": {"staff_id": "staff_1", "staff_position": 0.0, "page_number": 1},
                "hand_assignment": {"hand": "left", "confidence": 0.9, "alternatives": []},
                "confidence": {"overall": 0.9},
            },
        ],
        "chords": [],
        "voices": [],
    }


def test_ir_to_model_adapter(sample_ir_v1):
    """Test IR-to-model conversion."""
    adapter = IRToModelAdapter(uncertainty_policy="mle")

    result = adapter.convert(sample_ir_v1)

    # Check structure
    assert "features_by_hand" in result
    assert "note_sequences_by_hand" in result
    assert "metadata" in result

    # Check features
    assert "left" in result["features_by_hand"]
    assert "right" in result["features_by_hand"]

    # Check tensor shapes
    right_features = result["features_by_hand"]["right"]
    assert isinstance(right_features, torch.Tensor)
    assert right_features.shape[0] == 1  # 1 right-hand note
    assert right_features.shape[1] > 0  # Feature dimension

    left_features = result["features_by_hand"]["left"]
    assert isinstance(left_features, torch.Tensor)
    assert left_features.shape[0] == 1  # 1 left-hand note


def test_feature_extraction():
    """Test that features are extracted correctly."""
    adapter = IRToModelAdapter(
        uncertainty_policy="mle",
        include_ioi=True,
        include_duration=True,
        include_metric_position=True,
        include_chord_info=True,
    )

    feature_dim = adapter._get_feature_dim()

    # 3 (pitch features) + 1 (duration) + 1 (IOI) + 1 (metric) + 2 (chord) = 8
    assert feature_dim == 8


def test_model_to_ir_adapter(sample_ir_v1):
    """Test Model-to-IR conversion."""
    # Create mock predictions
    predictions_by_hand = {
        "right": {
            "hand": "right",
            "sequence_length": 1,
            "predictions": [
                {
                    "position": 0,
                    "finger": 1,
                    "confidence": 0.9,
                    "alternatives": [{"finger": 2, "confidence": 0.1}],
                }
            ],
        },
        "left": {
            "hand": "left",
            "sequence_length": 1,
            "predictions": [
                {
                    "position": 0,
                    "finger": 5,
                    "confidence": 0.85,
                    "alternatives": [],
                }
            ],
        },
    }

    note_sequences_by_hand = {
        "right": [{"note_id": "note_1", "pitch": 60, "onset_seconds": 0.0}],
        "left": [{"note_id": "note_2", "pitch": 48, "onset_seconds": 0.0}],
    }

    adapter = ModelToIRAdapter(
        model_name="PRamoneda-ArLSTM",
        model_version="1.0.0",
        adapter_version="1.0.0",
        uncertainty_policy="mle",
    )

    ir_v2 = adapter.annotate_ir(sample_ir_v1, predictions_by_hand, note_sequences_by_hand)

    # Check version updated
    assert ir_v2["version"] == "2.0.0"

    # Check fingering annotations
    assert "fingering_metadata" in ir_v2
    assert ir_v2["fingering_metadata"]["notes_annotated"] == 2
    assert ir_v2["fingering_metadata"]["coverage"] == 1.0

    # Check notes have fingering
    note_1 = next(n for n in ir_v2["notes"] if n["note_id"] == "note_1")
    assert "fingering" in note_1
    assert note_1["fingering"]["finger"] == 1
    assert note_1["fingering"]["hand"] == "right"


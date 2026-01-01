"""Tests for quantization and voice resolvers."""

import pytest

from app.resolvers.quantization import QuantizationResolver
from app.resolvers.voice_resolver import VoiceResolver


def test_quantization_resolver():
    """Test quantization of note durations."""
    resolver = QuantizationResolver(tolerance=0.05, min_duration=0.0625)

    # Test standard durations
    assert resolver._quantize_duration(1.0) == 1.0  # Quarter note
    assert resolver._quantize_duration(0.5) == 0.5  # Eighth note
    assert resolver._quantize_duration(2.0) == 2.0  # Half note

    # Test dotted notes
    assert resolver._quantize_duration(1.5) == 1.5  # Dotted quarter
    assert resolver._quantize_duration(0.75) == 0.75  # Dotted eighth

    # Test note type conversion
    note_type, dots = resolver._duration_to_note_type(1.0)
    assert note_type == "quarter"
    assert dots == 0

    note_type, dots = resolver._duration_to_note_type(1.5)
    assert note_type == "quarter"
    assert dots == 1


def test_voice_resolver():
    """Test voice assignment for polyphonic music."""
    resolver = VoiceResolver(max_voices=4)

    # Create test notes (simultaneous chord)
    notes = [
        {
            "note_id": "n1",
            "pitch": {"midi_note": 60},  # C4
            "time": {"onset_seconds": 0.0},
            "spatial": {"staff_id": "staff_0"},
        },
        {
            "note_id": "n2",
            "pitch": {"midi_note": 64},  # E4
            "time": {"onset_seconds": 0.0},
            "spatial": {"staff_id": "staff_0"},
        },
        {
            "note_id": "n3",
            "pitch": {"midi_note": 67},  # G4
            "time": {"onset_seconds": 0.0},
            "spatial": {"staff_id": "staff_0"},
        },
    ]

    resolved = resolver.resolve_voices(notes, "staff_0")

    # Check that voices are assigned
    assert "resolved_voice" in resolved[0]
    assert "resolved_voice" in resolved[1]
    assert "resolved_voice" in resolved[2]

    # Higher pitches should get lower voice numbers (voice 1 = highest)
    # G4 (67) > E4 (64) > C4 (60)
    assert resolved[2]["resolved_voice"] == 1  # G4 (highest)
    assert resolved[1]["resolved_voice"] == 2  # E4
    assert resolved[0]["resolved_voice"] == 3  # C4 (lowest)


"""Tests for MIDI converter."""

import pytest
import mido

from app.converters.ir_to_midi import IRToMIDIConverter


def test_midi_converter_basic():
    """Test basic MIDI conversion."""
    converter = IRToMIDIConverter(tempo=120)

    ir_v2 = {
        "version": "2.0.0",
        "schema_type": "symbolic_score_ir",
        "time_signature": {"numerator": 4, "denominator": 4},
        "tempo": {"bpm": 120, "beat_unit": "quarter", "changes": []},
        "notes": [
            {
                "note_id": "n1",
                "pitch": {"midi_note": 60},  # C4
                "time": {"absolute_beat": 0.0},
                "duration": {"duration_beats": 1.0},
            },
            {
                "note_id": "n2",
                "pitch": {"midi_note": 64},  # E4
                "time": {"absolute_beat": 1.0},
                "duration": {"duration_beats": 1.0},
            },
        ],
    }

    midi_bytes = converter.convert(ir_v2)

    # Validate MIDI file
    import io
    mid = mido.MidiFile(file=io.BytesIO(midi_bytes))
    assert len(mid.tracks) > 0

    # Check for note events
    note_ons = [msg for msg in mid.tracks[0] if msg.type == "note_on"]
    assert len(note_ons) >= 2


def test_midi_events():
    """Test MIDI event generation."""
    converter = IRToMIDIConverter()

    notes = [
        {
            "note_id": "n1",
            "pitch": {"midi_note": 60},
            "time": {"absolute_beat": 0.0},
            "duration": {"duration_beats": 1.0},
        }
    ]

    events = converter._notes_to_midi_events(notes)

    # Should have note_on and note_off
    assert len(events) == 2
    assert events[0]["type"] == "note_on"
    assert events[1]["type"] == "note_off"
    assert events[0]["note"] == 60
    assert events[1]["note"] == 60


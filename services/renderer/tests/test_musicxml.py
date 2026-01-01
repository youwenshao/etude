"""Tests for MusicXML converter."""

import pytest
from lxml import etree

from app.converters.ir_to_musicxml import IRToMusicXMLConverter


def test_musicxml_converter_basic():
    """Test basic MusicXML conversion."""
    converter = IRToMusicXMLConverter()

    # Minimal IR v2
    ir_v2 = {
        "version": "2.0.0",
        "schema_type": "symbolic_score_ir",
        "metadata": {
            "title": "Test Piece",
            "composer": "Test Composer",
        },
        "time_signature": {"numerator": 4, "denominator": 4, "changes": []},
        "key_signature": {"fifths": 0, "mode": "major"},
        "tempo": {"bpm": 120, "beat_unit": "quarter", "changes": []},
        "staves": [{"staff_id": "staff_0", "clef": "treble", "part_name": "Piano"}],
        "notes": [
            {
                "note_id": "n1",
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
                    "beat_fraction": "0/1",
                    "absolute_beat": 0.0,
                    "quantization_confidence": 1.0,
                },
                "duration": {
                    "duration_seconds": 1.0,
                    "duration_beats": 1.0,
                    "duration_fraction": "1/1",
                    "note_type": "quarter",
                    "dots": 0,
                },
                "spatial": {
                    "staff_id": "staff_0",
                    "staff_position": 0.0,
                    "page_number": 1,
                    "bounding_box": {"x": 0, "y": 0, "width": 10, "height": 10},
                    "staff_assignment_confidence": 1.0,
                },
                "confidence": {
                    "pitch_confidence": 1.0,
                    "duration_confidence": 1.0,
                    "onset_confidence": 1.0,
                },
            }
        ],
        "chords": [],
        "voices": [],
        "fingering_metadata": {
            "model_name": "test",
            "model_version": "1.0.0",
            "ir_to_model_adapter_version": "1.0.0",
            "model_to_ir_adapter_version": "1.0.0",
            "uncertainty_policy": "mle",
            "notes_annotated": 0,
            "coverage": 0.0,
        },
    }

    musicxml = converter.convert(ir_v2)

    # Parse and validate XML
    root = etree.fromstring(musicxml.encode())
    assert root.tag == "score-partwise"
    assert root.get("version") == "4.0"

    # Check for part
    parts = root.findall(".//part")
    assert len(parts) > 0


def test_musicxml_with_fingering():
    """Test MusicXML conversion with fingering annotations."""
    converter = IRToMusicXMLConverter(include_fingering=True)

    ir_v2 = {
        "version": "2.0.0",
        "schema_type": "symbolic_score_ir",
        "metadata": {"title": "Test"},
        "time_signature": {"numerator": 4, "denominator": 4, "changes": []},
        "key_signature": {"fifths": 0, "mode": "major"},
        "tempo": {"bpm": 120, "beat_unit": "quarter", "changes": []},
        "staves": [{"staff_id": "staff_0", "clef": "treble"}],
        "notes": [
            {
                "note_id": "n1",
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
                    "beat_fraction": "0/1",
                    "absolute_beat": 0.0,
                    "quantization_confidence": 1.0,
                },
                "duration": {
                    "duration_seconds": 1.0,
                    "duration_beats": 1.0,
                    "duration_fraction": "1/1",
                    "note_type": "quarter",
                    "dots": 0,
                },
                "spatial": {
                    "staff_id": "staff_0",
                    "staff_position": 0.0,
                    "page_number": 1,
                    "bounding_box": {"x": 0, "y": 0, "width": 10, "height": 10},
                    "staff_assignment_confidence": 1.0,
                },
                "fingering": {
                    "finger": 1,
                    "hand": "right",
                    "confidence": 0.9,
                    "alternatives": [],
                    "model_name": "test",
                    "model_version": "1.0.0",
                    "adapter_version": "1.0.0",
                    "uncertainty_policy": "mle",
                },
                "confidence": {
                    "pitch_confidence": 1.0,
                    "duration_confidence": 1.0,
                    "onset_confidence": 1.0,
                },
            }
        ],
        "chords": [],
        "voices": [],
        "fingering_metadata": {
            "model_name": "test",
            "model_version": "1.0.0",
            "ir_to_model_adapter_version": "1.0.0",
            "model_to_ir_adapter_version": "1.0.0",
            "uncertainty_policy": "mle",
            "notes_annotated": 1,
            "coverage": 1.0,
        },
    }

    musicxml = converter.convert(ir_v2)

    # Check for fingering element
    root = etree.fromstring(musicxml.encode())
    fingering = root.find(".//fingering")
    assert fingering is not None
    assert fingering.text == "1"
    assert fingering.get("placement") == "above"  # Right hand


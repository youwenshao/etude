"""Unit tests for OMR service."""

import pytest
import numpy as np

from app.adapters.ir_adapter import OMRToIRAdapter
from app.models.omr_model import OMRModel
from app.utils.pdf_processor import PDFProcessor


def test_omr_model_placeholder():
    """Test OMR model placeholder predictions."""
    model = OMRModel(
        model_path="/nonexistent/path.pt",
        device="cpu",
        confidence_threshold=0.5,
    )

    # Create a dummy image
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    # Get predictions
    predictions = model.predict(image)

    # Verify structure
    assert "notes" in predictions
    assert "time_signature" in predictions
    assert "key_signature" in predictions
    assert "tempo" in predictions
    assert "staves" in predictions


def test_pdf_processor_validation():
    """Test PDF processor validation."""
    processor = PDFProcessor(dpi=300, max_pages=50)

    # Valid PDF header
    valid_pdf = b"%PDF-1.4\n" + b"x" * 1000
    processor.validate_pdf(valid_pdf, max_size_mb=1)

    # Invalid PDF header
    invalid_pdf = b"NOT A PDF" + b"x" * 1000
    with pytest.raises(ValueError, match="Invalid PDF file"):
        processor.validate_pdf(invalid_pdf, max_size_mb=1)

    # File too large
    large_pdf = b"%PDF-1.4\n" + b"x" * (60 * 1024 * 1024)  # 60 MB
    with pytest.raises(ValueError, match="too large"):
        processor.validate_pdf(large_pdf, max_size_mb=50)


def test_ir_adapter_conversion():
    """Test IR adapter conversion."""
    adapter = OMRToIRAdapter(
        source_pdf_artifact_id="test-artifact-123",
        model_name="test-model",
        model_version="1.0.0",
    )

    # Create mock OMR predictions
    omr_predictions = [
        {
            "notes": [
                {
                    "pitch": {"midi": 60, "name": "C4"},
                    "onset_time": 0.0,
                    "duration": 0.5,
                    "staff": 0,
                    "position": {"x": 100, "y": 200},
                    "confidence": 0.95,
                }
            ],
            "time_signature": {"numerator": 4, "denominator": 4},
            "key_signature": {"fifths": 0, "mode": "major"},
            "tempo": {"bpm": 120},
            "staves": [
                {"staff_id": 0, "clef": "treble"},
                {"staff_id": 1, "clef": "bass"},
            ],
        }
    ]

    # Convert to IR
    ir_data = adapter.convert(omr_predictions, "test.pdf")

    # Verify IR structure
    assert ir_data["version"] == "1.0.0"
    assert ir_data["schema_type"] == "symbolic_score_ir"
    assert "metadata" in ir_data
    assert "notes" in ir_data
    assert "chords" in ir_data
    assert "voices" in ir_data
    assert len(ir_data["notes"]) > 0

    # Verify note structure
    note = ir_data["notes"][0]
    assert "note_id" in note
    assert "pitch" in note
    assert "time" in note
    assert "duration" in note
    assert "spatial" in note
    assert "confidence" in note


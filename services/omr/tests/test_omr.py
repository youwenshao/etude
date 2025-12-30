"""Unit tests for OMR service with Polyphonic-TrOMR integration."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
import torch

from app.adapters.ir_adapter import OMRToIRAdapter
from app.config import settings
from app.models.omr_model import OMRModel
from app.utils.pdf_processor import PDFProcessor


@pytest.fixture
def mock_staff_to_score():
    """Create a mock StaffToScore instance."""
    mock = MagicMock()
    mock.model = MagicMock()
    mock.model.generate = MagicMock(
        return_value=(
            [[1, 2, 3]],  # rhythm tokens
            [[4, 5, 6]],  # pitch tokens
            [[7, 8, 9]],  # lift tokens
        )
    )
    mock.rhythmtokenizer = MagicMock()
    mock.pitchtokenizer = MagicMock()
    mock.lifttokenizer = MagicMock()
    mock.args = MagicMock()
    mock.args.max_height = 128
    mock.args.patch_size = 16
    mock.detokenize = MagicMock(
        side_effect=lambda tokens, tokenizer: [
            ["clef-G2", "keySignature-CM", "note-C4_eighth", "note-E4_quarter"]
        ]
    )
    mock.transform = MagicMock()
    mock.transform.return_value = {"image": torch.zeros(1, 128, 128)}
    return mock


@pytest.fixture
def sample_image():
    """Create a sample RGB image for testing."""
    return np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8)


@pytest.fixture
def sample_grayscale_image():
    """Create a sample grayscale image for testing."""
    return np.random.randint(0, 255, (200, 300), dtype=np.uint8)


class TestOMRModel:
    """Tests for OMRModel class."""

    @patch("app.models.omr_model.getconfig")
    @patch("app.models.omr_model.StaffToScore")
    @patch("app.models.omr_model.settings")
    def test_model_initialization(self, mock_settings, mock_staff_class, mock_getconfig):
        """Test OMR model initialization."""
        # Setup mocks
        mock_settings.device = "cpu"
        mock_settings.model_name = "Polyphonic-TrOMR"
        mock_settings.model_version = "1.0.0"
        mock_settings.get_tromr_config_path.return_value = Path("/fake/config.yaml")
        mock_settings.get_tromr_checkpoint_path.return_value = Path("/fake/checkpoint.pth")
        mock_settings.get_tromr_base_path.return_value = Path("/fake/tromr")

        mock_args = MagicMock()
        mock_getconfig.return_value = mock_args

        mock_staff = MagicMock()
        mock_staff.model = MagicMock()
        mock_staff.model.to = MagicMock()
        mock_staff_class.return_value = mock_staff

        # Mock file existence
        with patch("pathlib.Path.exists", return_value=True):
            with patch("torch.load", return_value={"state_dict": {}}):
                model = OMRModel(device="cpu")

        assert model.device.type == "cpu"
        assert model.confidence_threshold == 0.5
        assert model.temperature == 0.2

    @patch("app.models.omr_model.getconfig")
    @patch("app.models.omr_model.StaffToScore")
    def test_model_loading_missing_config(self, mock_staff_class, mock_getconfig):
        """Test model loading fails gracefully when config is missing."""
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="config file not found"):
                model = OMRModel(device="cpu")

    @patch("app.models.omr_model.getconfig")
    @patch("app.models.omr_model.StaffToScore")
    def test_model_loading_missing_checkpoint(self, mock_staff_class, mock_getconfig):
        """Test model loading fails gracefully when checkpoint is missing."""
        mock_settings = MagicMock()
        mock_settings.get_tromr_config_path.return_value = Path("/fake/config.yaml")
        mock_settings.get_tromr_checkpoint_path.return_value = Path("/fake/checkpoint.pth")

        with patch("app.models.omr_model.settings", mock_settings):
            with patch("pathlib.Path.exists", side_effect=[True, False]):
                with pytest.raises(FileNotFoundError, match="checkpoint file not found"):
                    model = OMRModel(device="cpu")

    def test_preprocess_image_rgb(self, sample_image):
        """Test image preprocessing with RGB input."""
        with patch("app.models.omr_model.settings") as mock_settings:
            mock_settings.device = "cpu"
            with patch.object(OMRModel, "_load_model", return_value=MagicMock()):
                model = OMRModel(device="cpu")

        preprocessed = model.preprocess_image(sample_image)
        assert preprocessed.shape == sample_image.shape
        assert len(preprocessed.shape) == 3
        assert preprocessed.shape[2] == 3  # RGB

    def test_preprocess_image_grayscale(self, sample_grayscale_image):
        """Test image preprocessing with grayscale input."""
        with patch("app.models.omr_model.settings") as mock_settings:
            mock_settings.device = "cpu"
            with patch.object(OMRModel, "_load_model", return_value=MagicMock()):
                model = OMRModel(device="cpu")

        preprocessed = model.preprocess_image(sample_grayscale_image)
        assert len(preprocessed.shape) == 3
        assert preprocessed.shape[2] == 3  # Converted to RGB

    def test_preprocess_image_rgba(self):
        """Test image preprocessing with RGBA input."""
        rgba_image = np.random.randint(0, 255, (200, 300, 4), dtype=np.uint8)

        with patch("app.models.omr_model.settings") as mock_settings:
            mock_settings.device = "cpu"
            with patch.object(OMRModel, "_load_model", return_value=MagicMock()):
                model = OMRModel(device="cpu")

        preprocessed = model.preprocess_image(rgba_image)
        assert len(preprocessed.shape) == 3
        assert preprocessed.shape[2] == 3  # Converted to RGB

    @patch("app.models.omr_model.settings")
    def test_pitch_to_midi(self, mock_settings):
        """Test pitch to MIDI conversion."""
        mock_settings.device = "cpu"
        with patch.object(OMRModel, "_load_model", return_value=MagicMock()):
            model = OMRModel(device="cpu")

        # Test various pitches
        assert model._pitch_to_midi("C4") == 60  # Middle C
        assert model._pitch_to_midi("C5") == 72  # C5
        assert model._pitch_to_midi("A4") == 69  # A4 (440 Hz)
        assert model._pitch_to_midi("F#4") == 66  # F#4

    @patch("app.models.omr_model.settings")
    def test_parse_note_token(self, mock_settings):
        """Test note token parsing."""
        mock_settings.device = "cpu"
        with patch.object(OMRModel, "_load_model", return_value=MagicMock()):
            model = OMRModel(device="cpu")

        # Test valid note token
        note_info = model._parse_note_token(
            "note-C4_eighth", "C4", ""
        )
        assert note_info is not None
        assert note_info["pitch"]["midi"] == 60
        assert note_info["duration"] == 0.5  # eighth note

        # Test with accidental
        note_info = model._parse_note_token(
            "note-F#4_quarter", "F#4", "#"
        )
        assert note_info is not None
        assert note_info["pitch"]["midi"] == 66

    @patch("app.models.omr_model.settings")
    def test_extract_clef(self, mock_settings):
        """Test clef extraction from token string."""
        mock_settings.device = "cpu"
        with patch.object(OMRModel, "_load_model", return_value=MagicMock()):
            model = OMRModel(device="cpu")

        assert model._extract_clef("clef-G2+keySignature-CM") == "treble"
        assert model._extract_clef("clef-F4+keySignature-CM") == "bass"
        assert model._extract_clef("note-C4_eighth") is None

    @patch("app.models.omr_model.settings")
    def test_extract_key_signature(self, mock_settings):
        """Test key signature extraction."""
        mock_settings.device = "cpu"
        with patch.object(OMRModel, "_load_model", return_value=MagicMock()):
            model = OMRModel(device="cpu")

        key_info = model._extract_key_signature("keySignature-CM+note-C4")
        assert key_info is not None
        assert key_info["mode"] == "major"

    @patch("app.models.omr_model.settings")
    def test_extract_note_tokens(self, mock_settings):
        """Test note token extraction."""
        mock_settings.device = "cpu"
        with patch.object(OMRModel, "_load_model", return_value=MagicMock()):
            model = OMRModel(device="cpu")

        rhythm_str = "clef-G2+keySignature-CM+note-C4_eighth+note-E4_quarter"
        pitch_str = "C4 E4"
        lift_str = "N N"

        notes = model._extract_note_tokens(rhythm_str, pitch_str, lift_str)
        assert len(notes) > 0
        assert "rhythm" in notes[0]
        assert "pitch" in notes[0]

    @patch("app.models.omr_model.settings")
    @patch("app.models.omr_model.StaffToScore")
    def test_predict(self, mock_staff_class, mock_settings, sample_image):
        """Test model prediction."""
        mock_settings.device = "cpu"
        mock_staff = MagicMock()
        mock_staff.model = MagicMock()
        mock_staff.model.generate = MagicMock(
            return_value=(
                [[1, 2, 3]],
                [[4, 5, 6]],
                [[7, 8, 9]],
            )
        )
        mock_staff.rhythmtokenizer = MagicMock()
        mock_staff.pitchtokenizer = MagicMock()
        mock_staff.lifttokenizer = MagicMock()
        mock_staff.args = MagicMock()
        mock_staff.args.max_height = 128
        mock_staff.args.patch_size = 16
        mock_staff.detokenize = MagicMock(
            return_value=[["clef-G2", "keySignature-CM", "note-C4_eighth"]]
        )
        mock_staff.transform = MagicMock()
        mock_staff.transform.return_value = {"image": torch.zeros(1, 128, 128)}

        with patch.object(OMRModel, "_load_model", return_value=mock_staff):
            model = OMRModel(device="cpu")

        predictions = model.predict(sample_image)

        assert "notes" in predictions
        assert "time_signature" in predictions
        assert "key_signature" in predictions
        assert "tempo" in predictions
        assert "staves" in predictions

    @patch("app.models.omr_model.settings")
    @patch("app.models.omr_model.StaffToScore")
    def test_predict_multi_page(self, mock_staff_class, mock_settings, sample_image):
        """Test multi-page prediction."""
        mock_settings.device = "cpu"
        mock_staff = MagicMock()
        mock_staff.model = MagicMock()
        mock_staff.model.generate = MagicMock(
            return_value=(
                [[1, 2, 3]],
                [[4, 5, 6]],
                [[7, 8, 9]],
            )
        )
        mock_staff.rhythmtokenizer = MagicMock()
        mock_staff.pitchtokenizer = MagicMock()
        mock_staff.lifttokenizer = MagicMock()
        mock_staff.args = MagicMock()
        mock_staff.args.max_height = 128
        mock_staff.args.patch_size = 16
        mock_staff.detokenize = MagicMock(
            return_value=[["clef-G2", "keySignature-CM", "note-C4_eighth"]]
        )
        mock_staff.transform = MagicMock()
        mock_staff.transform.return_value = {"image": torch.zeros(1, 128, 128)}

        with patch.object(OMRModel, "_load_model", return_value=mock_staff):
            model = OMRModel(device="cpu")

        images = [sample_image, sample_image]
        predictions = model.predict_multi_page(images)

        assert len(predictions) == 2
        assert all("page_number" in p for p in predictions)

    @patch("app.models.omr_model.settings")
    @patch("app.models.omr_model.StaffToScore")
    def test_predict_error_handling(self, mock_staff_class, mock_settings, sample_image):
        """Test error handling in prediction."""
        mock_settings.device = "cpu"
        mock_staff = MagicMock()
        mock_staff.model = MagicMock()
        mock_staff.model.generate = MagicMock(side_effect=RuntimeError("Model error"))
        mock_staff.args = MagicMock()
        mock_staff.args.max_height = 128
        mock_staff.args.patch_size = 16
        mock_staff.transform = MagicMock()
        mock_staff.transform.return_value = {"image": torch.zeros(1, 128, 128)}

        with patch.object(OMRModel, "_load_model", return_value=mock_staff):
            model = OMRModel(device="cpu")

        with pytest.raises(RuntimeError, match="Inference failed"):
            model.predict(sample_image)


class TestIRAdapter:
    """Tests for IR adapter with TrOMR output format."""

    def test_adapter_with_tromr_output(self):
        """Test adapter conversion with TrOMR-style output."""
        adapter = OMRToIRAdapter(
            source_pdf_artifact_id="test-artifact-123",
            model_name="Polyphonic-TrOMR",
            model_version="1.0.0",
        )

        # Create TrOMR-style predictions
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
                    },
                    {
                        "pitch": {"midi": 64, "name": "E4"},
                        "onset_time": 0.0,  # Simultaneous note (chord)
                        "duration": 0.5,
                        "staff": 0,
                        "position": {"x": 150, "y": 200},
                        "confidence": 0.92,
                    },
                ],
                "time_signature": {"numerator": 4, "denominator": 4},
                "key_signature": {"fifths": 0, "mode": "major"},
                "tempo": {"bpm": 120},
                "staves": [
                    {"staff_id": 0, "clef": "treble"},
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
        assert len(ir_data["notes"]) == 2

        # Verify chord detection (simultaneous notes)
        assert len(ir_data["chords"]) > 0

        # Verify Fraction handling in timing
        note = ir_data["notes"][0]
        assert "time" in note
        assert "duration" in note
        # Check that beat_fraction and duration_fraction are strings (Fraction serialized)
        assert isinstance(note["time"]["beat_fraction"], str)
        assert isinstance(note["duration"]["duration_fraction"], str)
        # Verify Fraction format (e.g., "1/4")
        assert "/" in note["time"]["beat_fraction"]
        assert "/" in note["duration"]["duration_fraction"]

    def test_adapter_fraction_handling(self):
        """Test that adapter properly handles Fraction objects."""
        adapter = OMRToIRAdapter(
            source_pdf_artifact_id="test-artifact-123",
            model_name="Polyphonic-TrOMR",
            model_version="1.0.0",
        )

        omr_predictions = [
            {
                "notes": [
                    {
                        "pitch": {"midi": 60, "name": "C4"},
                        "onset_time": 0.0,
                        "duration": 0.25,  # Quarter note
                        "staff": 0,
                        "position": {"x": 100, "y": 200},
                        "confidence": 0.95,
                    },
                ],
                "time_signature": {"numerator": 4, "denominator": 4},
                "key_signature": {"fifths": 0, "mode": "major"},
                "tempo": {"bpm": 120},
                "staves": [{"staff_id": 0, "clef": "treble"}],
            }
        ]

        ir_data = adapter.convert(omr_predictions, "test.pdf")
        note = ir_data["notes"][0]

        # Verify Fraction is properly serialized
        duration_frac = note["duration"]["duration_fraction"]
        assert isinstance(duration_frac, str)
        # Should be a valid fraction like "1/4" for quarter note
        parts = duration_frac.split("/")
        assert len(parts) == 2
        assert int(parts[0]) > 0
        assert int(parts[1]) > 0


class TestPDFProcessor:
    """Tests for PDF processor."""

    def test_pdf_processor_validation(self):
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


class TestDeviceConfiguration:
    """Tests for device configuration."""

    @patch("torch.backends.mps.is_available", return_value=True)
    @patch("torch.cuda.is_available", return_value=False)
    def test_mps_device_detection(self, mock_cuda, mock_mps):
        """Test MPS device detection."""
        from app.config import _detect_device

        device = _detect_device()
        assert device == "mps"

    @patch("torch.backends.mps.is_available", return_value=False)
    @patch("torch.cuda.is_available", return_value=True)
    def test_cuda_device_detection(self, mock_cuda, mock_mps):
        """Test CUDA device detection."""
        from app.config import _detect_device

        device = _detect_device()
        assert device == "cuda"

    @patch("torch.backends.mps.is_available", return_value=False)
    @patch("torch.cuda.is_available", return_value=False)
    def test_cpu_fallback(self, mock_cuda, mock_mps):
        """Test CPU fallback when no GPU available."""
        from app.config import _detect_device

        device = _detect_device()
        assert device == "cpu"


class TestTokenParsing:
    """Tests for TrOMR token parsing."""

    @patch("app.models.omr_model.settings")
    def test_parse_predictions_basic(self, mock_settings):
        """Test basic prediction parsing."""
        mock_settings.device = "cpu"
        with patch.object(OMRModel, "_load_model", return_value=MagicMock()):
            model = OMRModel(device="cpu")

        predrhythm = [["clef-G2", "keySignature-CM", "note-C4_eighth", "note-E4_quarter"]]
        predpitch = [["C4", "E4"]]
        predlift = [["N", "N"]]

        predictions = model._parse_predictions(
            predrhythm, predpitch, predlift, (200, 300, 3)
        )

        assert "notes" in predictions
        assert "time_signature" in predictions
        assert "key_signature" in predictions
        assert "staves" in predictions
        assert len(predictions["notes"]) > 0

    @patch("app.models.omr_model.settings")
    def test_parse_predictions_multiple_staves(self, mock_settings):
        """Test parsing predictions with multiple staves."""
        mock_settings.device = "cpu"
        with patch.object(OMRModel, "_load_model", return_value=MagicMock()):
            model = OMRModel(device="cpu")

        predrhythm = [
            ["clef-G2", "note-C4_eighth"],
            ["clef-F4", "note-C3_eighth"],
        ]
        predpitch = [["C4"], ["C3"]]
        predlift = [["N"], ["N"]]

        predictions = model._parse_predictions(
            predrhythm, predpitch, predlift, (200, 300, 3)
        )

        assert len(predictions["staves"]) >= 1
        assert len(predictions["notes"]) > 0

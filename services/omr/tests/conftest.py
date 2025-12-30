"""Pytest configuration and shared fixtures for OMR service tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Mock tromr imports before any app modules are imported
# This prevents import errors when tromr is not available
sys.modules["tromr"] = MagicMock()
sys.modules["tromr.configs"] = MagicMock()
sys.modules["tromr.staff2score"] = MagicMock()
sys.modules["tromr.model"] = MagicMock()
sys.modules["tromr.model.tromr_arch"] = MagicMock()

# Add service root to path for imports
service_root = Path(__file__).parent.parent
if str(service_root) not in sys.path:
    sys.path.insert(0, str(service_root))


@pytest.fixture(scope="session")
def tromr_repo_path():
    """Get path to Polyphonic-TrOMR repository."""
    service_root = Path(__file__).parent.parent
    tromr_path = service_root / "Polyphonic-TrOMR"
    return tromr_path


@pytest.fixture
def mock_tromr_config():
    """Mock TrOMR configuration."""
    return {
        "filepaths": {
            "checkpoint": "checkpoints/img2score_epoch47.pth",
            "lifttokenizer": "tokenizers/tokenizer_lift.json",
            "pitchtokenizer": "tokenizers/tokenizer_pitch.json",
            "rhythmtokenizer": "tokenizers/tokenizer_rhythm.json",
        },
        "max_height": 128,
        "patch_size": 16,
        "channels": 1,
    }


@pytest.fixture
def sample_rgb_image():
    """Create a sample RGB image."""
    return np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8)


@pytest.fixture
def sample_grayscale_image():
    """Create a sample grayscale image."""
    return np.random.randint(0, 255, (200, 300), dtype=np.uint8)


@pytest.fixture
def sample_omr_predictions():
    """Create sample OMR predictions in TrOMR format."""
    return [
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
                    "onset_time": 0.0,
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
            "metadata": {
                "page_number": 1,
                "image_width": 300,
                "image_height": 200,
            },
        }
    ]


@pytest.fixture(autouse=True)
def reset_model_singleton():
    """Reset the global model instance before each test."""
    # Clear the global model instance
    import app.models.omr_model as omr_module

    if hasattr(omr_module, "_model_instance"):
        omr_module._model_instance = None

    yield

    # Cleanup after test
    if hasattr(omr_module, "_model_instance"):
        omr_module._model_instance = None


"""API endpoint tests for OMR service."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_pdf_content():
    """Create mock PDF content."""
    # Minimal valid PDF
    return b"%PDF-1.4\n%EOF"


@pytest.fixture
def mock_omr_predictions():
    """Create mock OMR predictions."""
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
                }
            ],
            "time_signature": {"numerator": 4, "denominator": 4},
            "key_signature": {"fifths": 0, "mode": "major"},
            "tempo": {"bpm": 120},
            "staves": [{"staff_id": 0, "clef": "treble"}],
            "page_number": 1,
        }
    ]


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data

    @patch("app.main.get_omr_model")
    def test_health_check_with_model(self, mock_get_model, client):
        """Test health check with model loaded."""
        mock_model = MagicMock()
        mock_model.staff_to_score = MagicMock()
        mock_model.device = MagicMock()
        mock_model.device.__str__ = lambda x: "cpu"
        mock_get_model.return_value = mock_model

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("model_status") == "loaded"


class TestInfoEndpoint:
    """Tests for info endpoint."""

    def test_service_info(self, client):
        """Test service info endpoint."""
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "capabilities" in data


class TestProcessEndpoint:
    """Tests for PDF processing endpoint."""

    @patch("app.main.get_omr_model")
    @patch("app.main.PDFProcessor")
    def test_process_pdf_success(
        self, mock_pdf_processor_class, mock_get_model, client, mock_pdf_content, mock_omr_predictions
    ):
        """Test successful PDF processing."""
        # Mock PDF processor
        mock_processor = MagicMock()
        mock_processor.validate_pdf = MagicMock()
        mock_processor.pdf_to_images = MagicMock(
            return_value=[np.zeros((200, 300, 3), dtype=np.uint8)]
        )
        mock_pdf_processor_class.return_value = mock_processor

        # Mock OMR model
        mock_model = MagicMock()
        mock_model.predict_multi_page = MagicMock(return_value=mock_omr_predictions)
        mock_get_model.return_value = mock_model

        # Make request
        files = {"pdf_bytes": ("test.pdf", mock_pdf_content, "application/pdf")}
        data = {"source_pdf_artifact_id": "test-artifact-123"}

        response = client.post("/process", files=files, data=data)

        assert response.status_code == 200
        result = response.json()
        assert "ir_data" in result
        assert "processing_metadata" in result
        assert "confidence_summary" in result

    @patch("app.main.PDFProcessor")
    def test_process_pdf_invalid(self, mock_pdf_processor_class, client):
        """Test processing invalid PDF."""
        mock_processor = MagicMock()
        mock_processor.validate_pdf = MagicMock(
            side_effect=ValueError("Invalid PDF file")
        )
        mock_pdf_processor_class.return_value = mock_processor

        files = {"pdf_bytes": ("invalid.pdf", b"NOT A PDF", "application/pdf")}
        response = client.post("/process", files=files)

        assert response.status_code == 400

    @patch("app.main.get_omr_model")
    @patch("app.main.PDFProcessor")
    def test_process_pdf_model_error(
        self, mock_pdf_processor_class, mock_get_model, client, mock_pdf_content
    ):
        """Test processing with model error."""
        # Mock PDF processor
        mock_processor = MagicMock()
        mock_processor.validate_pdf = MagicMock()
        mock_processor.pdf_to_images = MagicMock(
            return_value=[np.zeros((200, 300, 3), dtype=np.uint8)]
        )
        mock_pdf_processor_class.return_value = mock_processor

        # Mock OMR model with error
        mock_model = MagicMock()
        mock_model.predict_multi_page = MagicMock(
            side_effect=RuntimeError("Model inference failed")
        )
        mock_get_model.return_value = mock_model

        files = {"pdf_bytes": ("test.pdf", mock_pdf_content, "application/pdf")}
        response = client.post("/process", files=files)

        assert response.status_code == 500


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data


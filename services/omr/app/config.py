"""OMR Service Configuration."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """OMR Service Configuration"""

    # Service info
    service_name: str = "omr-service"
    service_version: str = "1.0.0"

    # Model configuration
    model_name: str = "Polyphonic-TrOMR"
    model_version: str = "1.0.0"
    model_path: str = "/app/models/polyphonic_tromr_weights.pt"

    # Device configuration
    device: str = "cuda"  # "cuda" or "cpu"
    use_gpu: bool = True

    # Processing configuration
    max_pdf_pages: int = 50
    max_file_size_mb: int = 50
    pdf_dpi: int = 300  # DPI for PDF to image conversion

    # Inference configuration
    batch_size: int = 1
    confidence_threshold: float = 0.5  # Minimum confidence for detections

    # Performance
    max_workers: int = 2  # Number of concurrent OMR jobs
    request_timeout: int = 300  # Timeout in seconds

    # API configuration
    host: str = "0.0.0.0"
    port: int = 8001

    # Logging
    log_level: str = "INFO"

    class Config:
        env_prefix = "OMR_"
        case_sensitive = False


settings = Settings()


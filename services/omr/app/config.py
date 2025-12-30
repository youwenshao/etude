"""OMR Service Configuration."""

import os
from pathlib import Path
from typing import Optional

import torch
from pydantic_settings import BaseSettings


def _detect_device() -> str:
    """Detect available device with MPS priority for Apple Silicon."""
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda"
    else:
        return "cpu"


class Settings(BaseSettings):
    """OMR Service Configuration"""

    # Service info
    service_name: str = "omr-service"
    service_version: str = "1.0.0"

    # Model configuration
    model_name: str = "Polyphonic-TrOMR"
    model_version: str = "1.0.0"
    
    # Polyphonic-TrOMR paths (relative to service root)
    tromr_base_path: str = "Polyphonic-TrOMR"
    tromr_config_path: str = "Polyphonic-TrOMR/tromr/workspace/config.yaml"
    tromr_checkpoint_path: str = "Polyphonic-TrOMR/tromr/workspace/checkpoints/img2score_epoch47.pth"

    # Device configuration - auto-detect with MPS priority
    device: str = _detect_device()
    use_gpu: bool = True

    # Processing configuration
    max_pdf_pages: int = 50
    max_file_size_mb: int = 50
    pdf_dpi: int = 300  # DPI for PDF to image conversion

    # Inference configuration
    batch_size: int = 1
    confidence_threshold: float = 0.5  # Minimum confidence for detections
    temperature: float = 0.2  # Temperature for model generation

    # Performance
    max_workers: int = 2  # Number of concurrent OMR jobs
    request_timeout: int = 300  # Timeout in seconds

    # API configuration
    host: str = "0.0.0.0"
    port: int = 8001

    # Logging
    log_level: str = "INFO"

    def get_tromr_config_path(self) -> Path:
        """Get absolute path to TrOMR config file."""
        base = Path(__file__).parent.parent.parent
        return base / self.tromr_config_path

    def get_tromr_checkpoint_path(self) -> Path:
        """Get absolute path to TrOMR checkpoint file."""
        base = Path(__file__).parent.parent.parent
        return base / self.tromr_checkpoint_path

    def get_tromr_base_path(self) -> Path:
        """Get absolute path to TrOMR base directory."""
        base = Path(__file__).parent.parent.parent
        return base / self.tromr_base_path

    class Config:
        env_prefix = "OMR_"
        case_sensitive = False


settings = Settings()


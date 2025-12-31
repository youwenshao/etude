"""Fingering Service Configuration."""

import os
from pathlib import Path
from typing import Literal, Optional

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
    """Fingering Service Configuration"""

    # Service info
    service_name: str = "fingering-service"
    service_version: str = "1.0.0"

    # Model configuration
    model_name: str = "PRamoneda-Piano-Fingering"
    model_version: str = "1.0.0"
    model_type: Literal["arlstm", "argnn"] = "arlstm"  # Choose model architecture

    # Model paths
    arlstm_model_path: str = "/app/models/arlstm/best_model.pt"
    argnn_model_path: str = "/app/models/argnn/best_model.pt"

    # PRamoneda repository path
    pramoneda_base_path: str = "Automatic-Piano-Fingering"

    # Device configuration
    device: str = _detect_device()
    use_gpu: bool = True

    # Inference configuration
    batch_size: int = 32
    max_sequence_length: int = 512  # Maximum note sequence length

    # Uncertainty policy
    default_policy: Literal["mle", "sampling"] = "mle"
    sampling_iterations: int = 10  # For sampling-based aggregation (future)

    # Adapter configuration
    adapter_version: str = "1.0.0"

    # Feature extraction
    include_ioi: bool = True  # Inter-onset intervals
    include_duration: bool = True
    include_metric_position: bool = True
    include_chord_info: bool = True

    # Confidence thresholds
    min_confidence_threshold: float = 0.3
    high_confidence_threshold: float = 0.8

    # Performance
    max_workers: int = 2
    request_timeout: int = 180

    # API configuration
    host: str = "0.0.0.0"
    port: int = 8002

    # Logging
    log_level: str = "INFO"

    def get_pramoneda_base_path(self) -> Path:
        """Get absolute path to PRamoneda base directory."""
        base = Path(__file__).parent.parent.parent
        return base / self.pramoneda_base_path

    def get_model_path(self) -> Path:
        """Get absolute path to model weights based on model_type."""
        if self.model_type == "arlstm":
            return Path(self.arlstm_model_path)
        else:
            return Path(self.argnn_model_path)

    class Config:
        env_prefix = "FINGERING_"
        case_sensitive = False


settings = Settings()


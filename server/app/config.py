"""Application configuration using Pydantic Settings."""

import os
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_test_environment() -> bool:
    """Check if we're running in a test environment."""
    return "PYTEST_CURRENT_TEST" in os.environ or "pytest" in os.environ.get("_", "")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = (
        "sqlite+aiosqlite:///:memory:" if _is_test_environment() else ""
    )

    # MinIO/S3
    MINIO_ENDPOINT: str = (
        "localhost:9000" if _is_test_environment() else ""
    )
    MINIO_ACCESS_KEY: str = (
        "minioadmin" if _is_test_environment() else ""
    )
    MINIO_SECRET_KEY: str = (
        "minioadmin123" if _is_test_environment() else ""
    )
    MINIO_USE_SSL: bool = False
    MINIO_BUCKET_ARTIFACTS: str = "etude-artifacts"
    MINIO_BUCKET_PDFS: str = "etude-pdfs"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = (
        "test-secret-key-change-in-production" if _is_test_environment() else ""
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS - Allow common development ports (Flutter web uses various ports)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080,http://localhost:5000,http://localhost:5001,http://localhost:5002,http://localhost:5003,http://localhost:5004,http://localhost:5005"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # OMR Service
    OMR_SERVICE_URL: str = Field(
        default="http://omr:8001",
        description="Base URL for OMR service",
    )

    # Fingering Service
    FINGERING_SERVICE_URL: str = Field(
        default="http://fingering-service:8002",
        description="Base URL for Fingering service",
    )

    # Renderer Service
    RENDERER_SERVICE_URL: str = Field(
        default="http://renderer-service:8003",
        description="Base URL for Renderer service",
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"


settings = Settings()


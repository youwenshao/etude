"""Renderer Service Configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Renderer Service Configuration"""

    # Service info
    service_name: str = "renderer-service"
    service_version: str = "1.0.0"

    # Output format configuration
    default_musicxml_version: str = "4.0"
    default_midi_tempo: int = 120
    default_svg_scale: int = 40  # Verovio scale

    # Resolution settings
    quantization_tolerance: float = 0.05  # 50ms tolerance for quantization
    min_note_duration: float = 0.0625  # Minimum duration (1/16 beat)

    # Voice resolution
    max_voices_per_staff: int = 4
    voice_crossing_penalty: float = 0.5

    # Layout settings
    measures_per_system: int = 4
    systems_per_page: int = 4

    # MusicXML settings
    include_fingering: bool = True
    include_dynamics: bool = True
    include_articulations: bool = True

    # SVG settings
    svg_page_height: int = 2970  # A4 height in pixels
    svg_page_width: int = 2100  # A4 width in pixels
    svg_page_margin: int = 100

    # Caching
    enable_cache: bool = True
    cache_ttl: int = 3600  # 1 hour

    # Performance
    max_workers: int = 2
    request_timeout: int = 120

    # API configuration
    host: str = "0.0.0.0"
    port: int = 8003

    # Logging
    log_level: str = "INFO"

    class Config:
        env_prefix = "RENDERER_"
        case_sensitive = False


settings = Settings()


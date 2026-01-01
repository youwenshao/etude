"""Renderer Service FastAPI application."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response, JSONResponse
import logging
from typing import Dict, Any, List, Optional, Literal
import hashlib
import time
import copy

from app.config import settings
from app.converters.ir_to_musicxml import IRToMusicXMLConverter
from app.converters.ir_to_midi import IRToMIDIConverter
from app.converters.ir_to_svg import IRToSVGConverter
from app.resolvers.quantization import QuantizationResolver
from app.resolvers.voice_resolver import VoiceResolver
from app.schemas.response import RenderResponse, HealthResponse

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Étude Renderer Service",
    description="Convert Symbolic IR to MusicXML, MIDI, and SVG formats",
    version=settings.service_version,
)

# Simple in-memory cache
_cache: Dict[str, Any] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize converters on startup."""
    logger.info("Starting Renderer Service")
    logger.info(f"Version: {settings.service_version}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        version=settings.service_version,
    )


@app.post("/render", response_model=RenderResponse)
async def render(
    ir_v2: Dict[str, Any],
    formats: List[Literal["musicxml", "midi", "svg"]] = Query(default=["musicxml"]),
    use_cache: bool = True,
):
    """
    Render Symbolic IR v2 to requested formats.

    Args:
        ir_v2: Symbolic Score IR v2 with fingering
        formats: List of output formats to generate
        use_cache: Whether to use cached results

    Returns:
        Rendered outputs in requested formats
    """
    start_time = time.time()

    logger.info(f"Render request for formats: {formats}")
    logger.info(
        f"IR version: {ir_v2.get('version')}, Notes: {len(ir_v2.get('notes', []))}"
    )

    # Generate cache key
    cache_key = None
    if use_cache and settings.enable_cache:
        cache_key = _generate_cache_key(ir_v2, formats)
        if cache_key in _cache:
            logger.info("Returning cached result")
            return _cache[cache_key]

    try:
        # Step 1: Resolve ambiguities
        resolved_ir = _resolve_ambiguities(ir_v2)

        # Step 2: Generate requested formats
        results = {}

        if "musicxml" in formats or "svg" in formats:
            musicxml = _generate_musicxml(resolved_ir)
            if "musicxml" in formats:
                results["musicxml"] = musicxml

            # Generate SVG if requested
            if "svg" in formats:
                svg_pages = _generate_svg(musicxml)
                results["svg"] = svg_pages

        if "midi" in formats:
            midi = _generate_midi(resolved_ir)
            results["midi"] = midi

        processing_time = time.time() - start_time

        response = RenderResponse(
            success=True,
            formats=results,
            processing_time_seconds=processing_time,
            message="Rendering completed successfully",
        )

        # Cache result
        if cache_key and settings.enable_cache:
            _cache[cache_key] = response

        logger.info(f"Rendering complete in {processing_time:.2f}s")

        return response

    except Exception as e:
        logger.error(f"Rendering error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Rendering failed: {str(e)}")


@app.post("/render/musicxml")
async def render_musicxml_only(ir_v2: Dict[str, Any]):
    """Render to MusicXML only (convenience endpoint)."""
    result = await render(ir_v2, formats=["musicxml"])

    return Response(
        content=result.formats["musicxml"],
        media_type="application/vnd.recordare.musicxml+xml",
        headers={"Content-Disposition": "attachment; filename=score.musicxml"},
    )


@app.post("/render/midi")
async def render_midi_only(ir_v2: Dict[str, Any]):
    """Render to MIDI only (convenience endpoint)."""
    result = await render(ir_v2, formats=["midi"])

    return Response(
        content=result.formats["midi"],
        media_type="audio/midi",
        headers={"Content-Disposition": "attachment; filename=score.mid"},
    )


@app.post("/render/svg")
async def render_svg_only(ir_v2: Dict[str, Any]):
    """Render to SVG only (convenience endpoint)."""
    result = await render(ir_v2, formats=["svg"])

    # Return first page or all pages as JSON
    svg_pages = result.formats["svg"]
    if len(svg_pages) == 1:
        return Response(
            content=svg_pages[0],
            media_type="image/svg+xml",
            headers={"Content-Disposition": "attachment; filename=score.svg"},
        )
    else:
        # Return as JSON with all pages
        return JSONResponse(
            content={"pages": svg_pages, "page_count": len(svg_pages)},
            headers={"Content-Disposition": "attachment; filename=score_pages.json"},
        )


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "supported_formats": ["musicxml", "midi", "svg"],
        "status": "running",
    }


def _generate_cache_key(ir_v2: Dict[str, Any], formats: List[str]) -> str:
    """Generate cache key from IR and format list."""
    import json

    content = json.dumps(ir_v2, sort_keys=True) + "|" + ",".join(sorted(formats))
    return hashlib.sha256(content.encode()).hexdigest()


def _resolve_ambiguities(ir_v2: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve timing and voice ambiguities."""
    logger.info("Resolving ambiguities")

    resolved_ir = copy.deepcopy(ir_v2)

    # Quantize timing
    quantizer = QuantizationResolver(
        tolerance=settings.quantization_tolerance,
        min_duration=settings.min_note_duration,
    )
    resolved_ir["notes"] = quantizer.quantize_notes(resolved_ir["notes"])

    # Resolve voices per staff
    voice_resolver = VoiceResolver(
        max_voices=settings.max_voices_per_staff,
        crossing_penalty=settings.voice_crossing_penalty,
    )

    for staff in resolved_ir["staves"]:
        resolved_ir["notes"] = voice_resolver.resolve_voices(
            resolved_ir["notes"], staff["staff_id"]
        )

    logger.info("Ambiguities resolved")

    return resolved_ir


def _generate_musicxml(ir_v2: Dict[str, Any]) -> str:
    """Generate MusicXML from resolved IR."""
    logger.info("Generating MusicXML")

    converter = IRToMusicXMLConverter(
        include_fingering=settings.include_fingering,
        include_dynamics=settings.include_dynamics,
        musicxml_version=settings.default_musicxml_version,
    )

    musicxml = converter.convert(ir_v2)

    return musicxml


def _generate_midi(ir_v2: Dict[str, Any]) -> bytes:
    """Generate MIDI from resolved IR."""
    logger.info("Generating MIDI")

    converter = IRToMIDIConverter(
        tempo=ir_v2.get("tempo", {}).get("bpm", settings.default_midi_tempo)
    )

    midi_bytes = converter.convert(ir_v2)

    return midi_bytes


def _generate_svg(musicxml: str) -> List[str]:
    """Generate SVG pages from MusicXML."""
    logger.info("Generating SVG")

    converter = IRToSVGConverter(
        scale=settings.default_svg_scale,
        page_height=settings.svg_page_height,
        page_width=settings.svg_page_width,
        page_margin=settings.svg_page_margin,
    )

    svg_pages = converter.convert(musicxml)

    return svg_pages


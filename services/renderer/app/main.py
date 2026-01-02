"""Renderer Service FastAPI application."""

from fastapi import FastAPI, HTTPException, Query, Body, Request
from fastapi.responses import Response, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.applications import Starlette
from starlette.exceptions import ExceptionMiddleware
import logging
from typing import Dict, Any, List, Optional, Literal, Callable
import hashlib
import time
import copy
import traceback
import json

from app.config import settings
from app.converters.ir_to_musicxml import IRToMusicXMLConverter
from app.converters.ir_to_midi import IRToMIDIConverter
from app.converters.ir_to_svg import IRToSVGConverter
from app.converters.ir_to_png import IRToPNGConverter
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

# Note: Exception handlers are registered below after middleware

# Simple in-memory cache
_cache: Dict[str, Any] = {}


class ExceptionSafeMiddleware(BaseHTTPMiddleware):
    """Middleware to catch all exceptions and ensure JSON responses."""
    
    async def dispatch(self, request: StarletteRequest, call_next: Callable) -> StarletteResponse:
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Catch any exception that bypasses exception handlers
            error_traceback = traceback.format_exc()
            error_type = type(exc).__name__
            error_message = str(exc)
            
            # Log the error
            try:
                logger.error(
                    f"Middleware caught exception in {request.url.path}: {error_type}: {error_message}\n{error_traceback}",
                    extra={
                        "error_type": error_type,
                        "error_message": error_message,
                        "path": str(request.url.path),
                        "method": request.method,
                    }
                )
            except Exception:
                # If logging fails, at least try to log to stderr
                print(f"CRITICAL: Failed to log error: {error_type}: {error_message}")
            
            # Always return JSON response
            try:
                include_traceback = settings.log_level.upper() == "DEBUG"
                error_detail = {
                    "error": f"{error_type}: {error_message}",
                    "error_type": error_type,
                    "message": error_message,
                }
                if include_traceback:
                    error_detail["traceback"] = error_traceback
                
                return JSONResponse(
                    status_code=500,
                    content={"detail": error_detail},
                    headers={"Content-Type": "application/json"},
                )
            except Exception as json_error:
                # If even JSONResponse creation fails, return minimal JSON
                try:
                    return JSONResponse(
                        status_code=500,
                        content={"detail": {"error": "Internal server error", "error_type": "UnknownError"}},
                        headers={"Content-Type": "application/json"},
                    )
                except Exception:
                    # Last resort - create a simple JSON response manually
                    from starlette.responses import Response
                    return Response(
                        content=json.dumps({"detail": {"error": "Internal server error"}}).encode(),
                        status_code=500,
                        media_type="application/json",
                    )


# Add middleware to catch exceptions early
app.add_middleware(ExceptionSafeMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages."""
    logger.error(f"Validation error: {exc.errors()}, body: {exc.body}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body)[:500] if exc.body else None},
        headers={"Content-Type": "application/json"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPException and ensure JSON response."""
    try:
        # Extract job_id if available
        job_id = request.headers.get("X-Job-Id", "unknown")
        
        logger.error(
            f"Job {job_id}: HTTPException in {request.url.path}: {exc.status_code}: {exc.detail}",
            extra={
                "job_id": job_id,
                "status_code": exc.status_code,
                "detail": str(exc.detail),
                "path": request.url.path,
            }
        )
        
        # Ensure detail is a dict or string
        if isinstance(exc.detail, dict):
            detail = exc.detail
        elif isinstance(exc.detail, (list, tuple)):
            detail = {"errors": exc.detail, "message": "Validation errors"}
        else:
            detail = {"error": str(exc.detail), "message": str(exc.detail)}
        
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detail},
            headers={"Content-Type": "application/json"},
        )
    except Exception as handler_error:
        # If handler itself fails, return minimal JSON
        logger.critical(f"HTTPException handler failed: {handler_error}")
        return JSONResponse(
            status_code=exc.status_code if hasattr(exc, 'status_code') else 500,
            content={"detail": {"error": "Internal server error", "original_status": exc.status_code if hasattr(exc, 'status_code') else 500}},
            headers={"Content-Type": "application/json"},
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions with detailed error messages."""
    try:
        # Don't handle HTTPException here - we have a separate handler
        if isinstance(exc, HTTPException):
            raise exc
        
        error_traceback = traceback.format_exc()
        error_type = type(exc).__name__
        error_message = str(exc)
        
        # Extract job_id if available
        job_id = request.headers.get("X-Job-Id", "unknown")
        
        # Log full error details
        try:
            logger.error(
                f"Job {job_id}: Unhandled exception in {request.url.path}: {error_type}: {error_message}\n{error_traceback}",
                extra={
                    "job_id": job_id,
                    "error_type": error_type,
                    "error_message": error_message,
                    "path": request.url.path,
                    "method": request.method,
                }
            )
        except Exception as log_error:
            # If logging fails, at least print
            print(f"CRITICAL: Failed to log error: {log_error}")
        
        # Include stack trace in development mode
        include_traceback = settings.log_level.upper() == "DEBUG"
        
        error_detail = {
            "error": f"{error_type}: {error_message}",
            "error_type": error_type,
            "message": error_message,
        }
        
        if include_traceback:
            error_detail["traceback"] = error_traceback
        
        return JSONResponse(
            status_code=500,
            content={"detail": error_detail},
            headers={"Content-Type": "application/json"},
        )
    except Exception as handler_error:
        # If handler itself fails, return minimal JSON
        logger.critical(f"Global exception handler failed: {handler_error}")
        try:
            return JSONResponse(
                status_code=500,
                content={"detail": {"error": "Internal server error", "error_type": "HandlerError"}},
                headers={"Content-Type": "application/json"},
            )
        except Exception:
            # Last resort - create JSON manually
            from starlette.responses import Response
            return Response(
                content=json.dumps({"detail": {"error": "Internal server error"}}).encode(),
                status_code=500,
                media_type="application/json",
            )


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
    request: Request,
    ir_v2: Dict[str, Any] = Body(..., description="Symbolic IR v2 data"),
    formats: List[Literal["musicxml", "midi", "svg", "png"]] = Query(default=["musicxml"]),
    use_cache: bool = Query(default=True, description="Whether to use cached results"),
):
    """
    Render Symbolic IR v2 to requested formats.

    Args:
        request: FastAPI request object
        ir_v2: Symbolic Score IR v2 with fingering
        formats: List of output formats to generate
        use_cache: Whether to use cached results

    Returns:
        Rendered outputs in requested formats
    """
    start_time = time.time()

    # Extract job_id from request headers if available for logging
    job_id = request.headers.get("X-Job-Id", "unknown")

    logger.info(f"Job {job_id}: Render request for formats: {formats}")
    logger.info(
        f"Job {job_id}: IR version: {ir_v2.get('version')}, Notes: {len(ir_v2.get('notes', []))}"
    )

    # Generate cache key
    cache_key = None
    if use_cache and settings.enable_cache:
        cache_key = _generate_cache_key(ir_v2, formats)
        if cache_key in _cache:
            logger.info(f"Job {job_id}: Returning cached result")
            return _cache[cache_key]
    
    try:
        # Comprehensive IR v2 validation before processing
        validation_errors = _validate_ir_v2(ir_v2)
        if validation_errors:
            error_msg = f"IR v2 validation failed: {'; '.join(validation_errors)}"
            logger.error(f"Job {job_id}: {error_msg}")
            raise ValueError(error_msg)
        
        logger.info(
            f"Job {job_id}: IR v2 validation passed: version={ir_v2.get('version')}, "
            f"notes={len(ir_v2.get('notes', []))}, staves={len(ir_v2.get('staves', []))}"
        )
        
        # Step 1: Resolve ambiguities
        try:
            logger.info(f"Job {job_id}: Resolving ambiguities")
            resolved_ir = _resolve_ambiguities(ir_v2)
            logger.info(f"Job {job_id}: Ambiguities resolved successfully")
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"Job {job_id}: Failed to resolve ambiguities: {type(e).__name__}: {e}\n{error_traceback}")
            raise ValueError(f"Failed to resolve ambiguities: {type(e).__name__}: {str(e)}") from e

        # Step 2: Generate requested formats with specific error handling
        results = {}

        if "musicxml" in formats or "svg" in formats or "png" in formats:
            try:
                logger.info(f"Job {job_id}: Generating MusicXML")
                musicxml = _generate_musicxml(resolved_ir)
                logger.info(f"Job {job_id}: MusicXML generated successfully ({len(musicxml)} chars)")
                if "musicxml" in formats:
                    results["musicxml"] = musicxml
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Job {job_id}: MusicXML generation failed: {type(e).__name__}: {e}\n{error_traceback}")
                raise ValueError(f"MusicXML generation failed: {type(e).__name__}: {str(e)}") from e

            # Generate SVG if requested
            if "svg" in formats:
                try:
                    logger.info(f"Job {job_id}: Generating SVG from MusicXML")
                    svg_pages = _generate_svg(musicxml)
                    logger.info(f"Job {job_id}: SVG generated successfully ({len(svg_pages)} pages)")
                    results["svg"] = svg_pages
                except Exception as e:
                    error_traceback = traceback.format_exc()
                    logger.error(f"Job {job_id}: SVG generation failed: {type(e).__name__}: {e}\n{error_traceback}")
                    raise ValueError(f"SVG generation failed: {type(e).__name__}: {str(e)}") from e

            # Generate PNG if requested
            if "png" in formats:
                try:
                    logger.info(f"Job {job_id}: Generating PNG from MusicXML")
                    png_pages = _generate_png(musicxml)
                    logger.info(f"Job {job_id}: PNG generated successfully ({len(png_pages)} pages)")
                    results["png"] = png_pages
                except Exception as e:
                    error_traceback = traceback.format_exc()
                    logger.error(f"Job {job_id}: PNG generation failed: {type(e).__name__}: {e}\n{error_traceback}")
                    raise ValueError(f"PNG generation failed: {type(e).__name__}: {str(e)}") from e

        if "midi" in formats:
            try:
                logger.info(f"Job {job_id}: Generating MIDI")
                midi = _generate_midi(resolved_ir)
                logger.info(f"Job {job_id}: MIDI generated successfully ({len(midi)} bytes)")
                results["midi"] = midi
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Job {job_id}: MIDI generation failed: {type(e).__name__}: {e}\n{error_traceback}")
                raise ValueError(f"MIDI generation failed: {type(e).__name__}: {str(e)}") from e

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

    except HTTPException:
        # Re-raise HTTPExceptions as-is (they already have proper detail)
        raise
    except ValueError as e:
        # Validation errors - return with 422 status
        error_traceback = traceback.format_exc()
        logger.error(f"Job {job_id}: Validation error: {type(e).__name__}: {e}\n{error_traceback}")
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "error": f"Validation error: {str(e)}",
                    "error_type": type(e).__name__,
                    "message": str(e),
                }
            },
        )
    except Exception as e:
        # Log full traceback for debugging
        error_traceback = traceback.format_exc()
        error_type = type(e).__name__
        error_message = str(e)
        
        logger.error(
            f"Job {job_id}: Rendering error: {error_type}: {error_message}\n{error_traceback}",
            extra={
                "job_id": job_id,
                "error_type": error_type,
                "error_message": error_message,
                "formats_requested": formats,
            }
        )
        
        # Include stack trace in development mode
        include_traceback = settings.log_level.upper() == "DEBUG"
        
        error_detail = {
            "error": f"Rendering failed: {error_type}: {error_message}",
            "error_type": error_type,
            "message": error_message,
            "formats_requested": formats,
        }
        
        if include_traceback:
            error_detail["traceback"] = error_traceback
        
        # Use JSONResponse directly to ensure proper serialization
        return JSONResponse(
            status_code=500,
            content={"detail": error_detail},
        )


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


@app.post("/render/png")
async def render_png_only(ir_v2: Dict[str, Any]):
    """Render to PNG only (convenience endpoint)."""
    result = await render(ir_v2, formats=["png"])

    # Return pages as JSON with base64-encoded PNG data
    png_pages = result.formats["png"]
    return JSONResponse(
        content={
            "pages": png_pages,
            "page_count": len(png_pages),
            "format": "base64-encoded PNG",
        },
        headers={"Content-Disposition": "attachment; filename=score_pages.json"},
    )


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "supported_formats": ["musicxml", "midi", "svg", "png"],
        "status": "running",
        "png_available": IRToPNGConverter.is_available(),
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


def _validate_ir_v2(ir_v2: Dict[str, Any]) -> List[str]:
    """
    Comprehensive validation of IR v2 structure.
    
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    
    # Basic structure validation
    if not isinstance(ir_v2, dict):
        errors.append(f"IR v2 must be a dictionary, got {type(ir_v2)}")
        return errors  # Can't continue if not a dict
    
    # Required top-level fields
    required_fields = ["notes", "staves", "metadata", "tempo", "time_signature", "key_signature"]
    for field in required_fields:
        if field not in ir_v2:
            errors.append(f"IR v2 missing required field '{field}'")
    
    # Validate notes
    if "notes" in ir_v2:
        if not isinstance(ir_v2["notes"], list):
            errors.append(f"IR v2 'notes' must be a list, got {type(ir_v2['notes'])}")
        else:
            # Validate note structure
            for i, note in enumerate(ir_v2["notes"]):
                if not isinstance(note, dict):
                    errors.append(f"Note {i} must be a dictionary, got {type(note)}")
                    continue
                
                required_note_fields = ["pitch", "time", "duration", "spatial"]
                for field in required_note_fields:
                    if field not in note:
                        errors.append(f"Note {i} missing required field '{field}'")
                
                # Validate pitch structure
                if "pitch" in note and isinstance(note["pitch"], dict):
                    if "midi_note" not in note["pitch"] and "pitch_class" not in note["pitch"]:
                        errors.append(f"Note {i} pitch missing 'midi_note' or 'pitch_class'")
                
                # Validate time structure
                if "time" in note and isinstance(note["time"], dict):
                    if "absolute_beat" not in note["time"] and "onset_seconds" not in note["time"]:
                        errors.append(f"Note {i} time missing 'absolute_beat' or 'onset_seconds'")
    
    # Validate staves
    if "staves" in ir_v2:
        if not isinstance(ir_v2["staves"], list):
            errors.append(f"IR v2 'staves' must be a list, got {type(ir_v2['staves'])}")
        else:
            for i, staff in enumerate(ir_v2["staves"]):
                if not isinstance(staff, dict):
                    errors.append(f"Staff {i} must be a dictionary, got {type(staff)}")
                    continue
                if "staff_id" not in staff:
                    errors.append(f"Staff {i} missing required field 'staff_id'")
    
    # Validate metadata
    if "metadata" in ir_v2 and not isinstance(ir_v2["metadata"], dict):
        errors.append(f"IR v2 'metadata' must be a dictionary, got {type(ir_v2['metadata'])}")
    
    # Validate tempo
    if "tempo" in ir_v2:
        if not isinstance(ir_v2["tempo"], dict):
            errors.append(f"IR v2 'tempo' must be a dictionary, got {type(ir_v2['tempo'])}")
        elif "bpm" not in ir_v2["tempo"]:
            errors.append("IR v2 'tempo' missing required field 'bpm'")
    
    # Validate time_signature
    if "time_signature" in ir_v2:
        if not isinstance(ir_v2["time_signature"], dict):
            errors.append(f"IR v2 'time_signature' must be a dictionary, got {type(ir_v2['time_signature'])}")
        else:
            if "numerator" not in ir_v2["time_signature"]:
                errors.append("IR v2 'time_signature' missing required field 'numerator'")
            if "denominator" not in ir_v2["time_signature"]:
                errors.append("IR v2 'time_signature' missing required field 'denominator'")
    
    # Validate key_signature
    if "key_signature" in ir_v2:
        if not isinstance(ir_v2["key_signature"], dict):
            errors.append(f"IR v2 'key_signature' must be a dictionary, got {type(ir_v2['key_signature'])}")
        else:
            if "fifths" not in ir_v2["key_signature"]:
                errors.append("IR v2 'key_signature' missing required field 'fifths'")
            if "mode" not in ir_v2["key_signature"]:
                errors.append("IR v2 'key_signature' missing required field 'mode'")
    
    return errors


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


def _generate_png(musicxml: str) -> List[str]:
    """Generate PNG pages from MusicXML (base64 encoded)."""
    logger.info("Generating PNG")

    if not IRToPNGConverter.is_available():
        raise ValueError(
            "PNG generation not available. "
            "CairoSVG is required: pip install cairosvg"
        )

    converter = IRToPNGConverter(
        scale=settings.default_svg_scale,
        page_height=settings.svg_page_height,
        page_width=settings.svg_page_width,
        page_margin=settings.svg_page_margin,
        dpi=getattr(settings, 'png_dpi', 150),  # Default 150 DPI
    )

    # Convert to base64-encoded PNG pages for JSON transport
    png_pages_base64 = converter.convert_to_base64(musicxml)

    return png_pages_base64


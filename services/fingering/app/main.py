"""Fingering Service FastAPI application."""

import time
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.fingering_model import get_fingering_model
from app.adapters.ir_to_model_adapter import IRToModelAdapter
from app.adapters.model_to_ir_adapter import ModelToIRAdapter
from app.policies.uncertainty_policy import get_policy
from app.schemas.request import FingeringRequest
from app.schemas.response import FingeringResponse, HealthResponse, ServiceInfo

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(
        "Starting Fingering AI Service",
        version=settings.service_version,
        model=settings.model_name,
        model_type=settings.model_type,
        device=settings.device,
    )

    # Preload fingering model at startup
    try:
        logger.info("Preloading fingering model...")
        model = get_fingering_model(settings.model_type)
        logger.info("Fingering model preloaded successfully", device=str(model.device))
    except Exception as e:
        logger.error(
            "Failed to preload fingering model",
            error=str(e),
            exc_info=True,
        )
        # Service can still start, but model will be loaded on first request
        logger.warning("Service will start but model loading will be deferred")

    yield

    # Shutdown
    logger.info("Shutting down Fingering AI Service")


# Create FastAPI app
app = FastAPI(
    title="Étude Fingering AI Service",
    description="Piano fingering inference service using PRamoneda model",
    version=settings.service_version,
    lifespan=lifespan,
)


@app.get("/health", status_code=200, response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check if model is loaded
        model = get_fingering_model(settings.model_type)
        model_status = "loaded" if model is not None else "not_loaded"
        return HealthResponse(
            status="healthy",
            service=settings.service_name,
            version=settings.service_version,
            model=settings.model_name,
            model_version=settings.model_version,
            model_type=settings.model_type,
            device=str(model.device) if model else settings.device,
            model_status=model_status,
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthResponse(
            status="unhealthy",
            service=settings.service_name,
            version=settings.service_version,
            model=settings.model_name,
            model_version=settings.model_version,
            model_type=settings.model_type,
            device=settings.device,
            model_status="error",
        )


@app.get("/info", status_code=200, response_model=ServiceInfo)
async def service_info():
    """Service metadata endpoint."""
    return ServiceInfo(
        service=settings.service_name,
        version=settings.service_version,
        model={
            "name": settings.model_name,
            "version": settings.model_version,
            "type": settings.model_type,
        },
        capabilities={
            "model_type": settings.model_type,
            "default_policy": settings.default_policy,
            "max_sequence_length": settings.max_sequence_length,
            "batch_size": settings.batch_size,
        },
    )


@app.post("/infer", status_code=200, response_model=FingeringResponse)
async def infer_fingering(request: FingeringRequest):
    """
    Infer fingering for a symbolic score (IR v1).

    Args:
        ir_v1: Symbolic Score IR v1 as JSON
        uncertainty_policy: "mle" or "sampling"

    Returns:
        Symbolic Score IR v2 with fingering annotations
    """
    start_time = time.time()

    ir_v1 = request.ir_v1
    uncertainty_policy = request.uncertainty_policy or settings.default_policy

    logger.info("Received fingering inference request")
    logger.info(
        "IR version",
        version=ir_v1.get("version", "unknown"),
        note_count=len(ir_v1.get("notes", [])),
        uncertainty_policy=uncertainty_policy,
    )

    try:
        # Initialize adapters
        ir_to_model_adapter = IRToModelAdapter(
            uncertainty_policy=uncertainty_policy,
            include_ioi=settings.include_ioi,
            include_duration=settings.include_duration,
            include_metric_position=settings.include_metric_position,
            include_chord_info=settings.include_chord_info,
        )

        # Convert IR v1 to model input
        model_input = ir_to_model_adapter.convert(ir_v1)

        # Get features and note sequences
        features_by_hand = model_input["features_by_hand"]
        note_sequences = model_input["note_sequences_by_hand"]

        logger.info(
            "Extracted features",
            left_hand_count=model_input["metadata"]["left_hand_count"],
            right_hand_count=model_input["metadata"]["right_hand_count"],
        )

        # Run fingering inference
        model = get_fingering_model(settings.model_type)
        predictions_by_hand = {}

        for hand in ["left", "right"]:
            if len(features_by_hand[hand]) > 0:
                predictions = model.predict(
                    features=features_by_hand[hand],
                    hand=hand,
                    return_alternatives=True,
                    top_k=2,
                )
                predictions_by_hand[hand] = predictions
                logger.info(
                    "Predicted fingering",
                    hand=hand,
                    note_count=len(predictions["predictions"]),
                )

        # Convert predictions back to IR v2
        model_to_ir_adapter = ModelToIRAdapter(
            model_name=settings.model_name,
            model_version=settings.model_version,
            adapter_version=ir_to_model_adapter.VERSION,
            uncertainty_policy=uncertainty_policy,
        )

        ir_v2 = model_to_ir_adapter.annotate_ir(
            ir_v1=ir_v1,
            predictions_by_hand=predictions_by_hand,
            note_sequences_by_hand=note_sequences,
        )

        processing_time = time.time() - start_time

        logger.info("Fingering inference complete", processing_time_seconds=processing_time)

        return FingeringResponse(
            success=True,
            symbolic_ir_v2=ir_v2,
            processing_time_seconds=processing_time,
            message="Fingering inference completed successfully",
        )

    except Exception as e:
        logger.error("Fingering inference error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fingering inference failed: {str(e)}",
        )


@app.get("/", status_code=200)
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "model": settings.model_name,
        "model_version": settings.model_version,
        "model_type": settings.model_type,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "info": "/info",
    }


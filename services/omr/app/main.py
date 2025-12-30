"""OMR Service FastAPI application."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.adapters.ir_adapter import OMRToIRAdapter
from app.config import settings
from app.models.omr_model import get_omr_model
from app.schemas.response import OMRProcessResponse, ServiceInfo
from app.utils.pdf_processor import PDFProcessor

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(
        "Starting OMR Service",
        version=settings.service_version,
        model=settings.model_name,
        device=settings.device,
    )

    # TODO: Load OMR model here if needed
    # from app.models.omr_model import get_omr_model
    # model = get_omr_model()

    yield

    # Shutdown
    logger.info("Shutting down OMR Service")


# Create FastAPI app
app = FastAPI(
    title="OMR Service",
    version=settings.service_version,
    description="Optical Music Recognition service for converting PDF sheet music to Symbolic IR",
    lifespan=lifespan,
)


@app.get("/health", status_code=200)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.service_name}


@app.get("/info", status_code=200, response_model=ServiceInfo)
async def service_info():
    """Service metadata endpoint."""
    return ServiceInfo(
        service=settings.service_name,
        version=settings.service_version,
        model={
            "name": settings.model_name,
            "version": settings.model_version,
        },
        capabilities={
            "max_pdf_pages": settings.max_pdf_pages,
            "max_file_size_mb": settings.max_file_size_mb,
            "pdf_dpi": settings.pdf_dpi,
        },
    )


@app.post("/process", status_code=200, response_model=OMRProcessResponse)
async def process_pdf(
    pdf_bytes: UploadFile = File(..., description="PDF file to process"),
    source_pdf_artifact_id: str = Form(None, description="Source PDF artifact ID"),
    filename: str = Form(None, description="Original filename"),
):
    """
    Process PDF and convert to Symbolic IR v1.

    - **pdf_bytes**: PDF file content (multipart/form-data)
    - **source_pdf_artifact_id**: Optional source artifact ID for lineage
    - **filename**: Optional original filename

    Returns Symbolic IR v1 as JSON.
    """
    start_time = time.time()

    try:
        # Read PDF bytes
        pdf_content = await pdf_bytes.read()
        actual_filename = filename or pdf_bytes.filename or "upload.pdf"

        # Validate PDF
        pdf_processor = PDFProcessor(
            dpi=settings.pdf_dpi, max_pages=settings.max_pdf_pages
        )
        pdf_processor.validate_pdf(pdf_content, settings.max_file_size_mb)

        # Convert PDF to images
        images = pdf_processor.pdf_to_images(pdf_content)
        logger.info(f"Converted PDF to {len(images)} page images")

        # Run OMR on all pages
        omr_model = get_omr_model()
        omr_predictions = omr_model.predict_multi_page(images)

        # Convert OMR predictions to IR
        adapter = OMRToIRAdapter(
            source_pdf_artifact_id=source_pdf_artifact_id or "unknown",
            model_name=settings.model_name,
            model_version=settings.model_version,
        )

        ir_data = adapter.convert(omr_predictions, actual_filename)

        # Calculate processing metadata
        processing_time = time.time() - start_time
        ir_data["metadata"]["generated_by"]["processing_time_seconds"] = (
            processing_time
        )

        # Calculate confidence summary
        notes = ir_data.get("notes", [])
        confidences = [n["confidence"]["overall"] for n in notes] if notes else [0.0]
        confidence_summary = {
            "average": sum(confidences) / len(confidences) if confidences else 0.0,
            "min": min(confidences) if confidences else 0.0,
            "max": max(confidences) if confidences else 0.0,
            "count": len(confidences),
        }

        processing_metadata = {
            "processing_time_seconds": processing_time,
            "pages_processed": len(images),
            "notes_detected": len(notes),
            "chords_detected": len(ir_data.get("chords", [])),
        }

        return OMRProcessResponse(
            ir_data=ir_data,
            processing_metadata=processing_metadata,
            confidence_summary=confidence_summary,
        )

    except ValueError as e:
        logger.error(f"PDF processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        logger.error(f"OMR processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal processing error: {str(e)}",
        )


@app.get("/", status_code=200)
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "docs": "/docs",
        "health": "/health",
        "info": "/info",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


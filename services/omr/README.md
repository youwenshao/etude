# OMR Service

Optical Music Recognition (OMR) microservice for converting PDF sheet music into Symbolic Score IR v1 format.

## Overview

The OMR service is a containerized microservice that:
- Processes uploaded PDF sheet music files
- Extracts musical notation (notes, rhythms, clefs, etc.) using OMR models
- Converts OMR output into the Symbolic Score IR v1 format
- Preserves uncertainty and confidence scores from the OMR model

## Architecture

The service consists of:
- **FastAPI application** - REST API for processing requests
- **OMR Model Wrapper** - Interface to Polyphonic-TrOMR or similar OMR models
- **PDF Processor** - Converts PDF pages to images for model input
- **IR Adapter** - Converts OMR predictions to Symbolic IR v1 format

## API Endpoints

- `POST /process` - Process PDF and return Symbolic IR v1
- `GET /health` - Health check
- `GET /info` - Service metadata

## Configuration

Configuration is managed via environment variables with `OMR_` prefix:

- `OMR_MODEL_PATH` - Path to model weights file
- `OMR_DEVICE` - Device to use (`cuda` or `cpu`)
- `OMR_MAX_PDF_PAGES` - Maximum pages to process (default: 50)
- `OMR_PDF_DPI` - DPI for PDF to image conversion (default: 300)
- `OMR_CONFIDENCE_THRESHOLD` - Minimum confidence for detections (default: 0.5)

## Development

### Local Development

```bash
cd services/omr
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### Docker Build

```bash
docker build -t etude-omr:latest ./services/omr
```

### Running with Docker Compose

The service is included in the main `docker-compose.yml` and runs on port 8001.

## Model Integration

Currently, the service uses placeholder/skeleton code for the OMR model. To integrate an actual OMR model:

1. Place model weights in `/app/models/` directory
2. Update `app/models/omr_model.py` with actual model loading logic
3. Implement the `predict()` method to return actual OMR predictions

## Testing

Run tests with:

```bash
cd services/omr
pytest tests/
```


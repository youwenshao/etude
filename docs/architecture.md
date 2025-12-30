# Étude Architecture

## System Overview

Étude is a research-grade pipeline for converting scanned sheet music (PDF) into accurate piano fingering annotations. The system uses a **symbolic-first architecture** where all machine learning operations work on a custom Symbolic Score Intermediate Representation (IR), rather than directly converting PDF to MusicXML.

## Core Principles

1. **Symbolic-First**: All ML models operate on a structured symbolic representation, not raw PDF pixels or MusicXML
2. **Versioned Artifacts**: Every transformation produces a versioned artifact with full lineage tracking
3. **Immutable Pipeline**: Artifacts are never modified; new versions are created for updates
4. **Research-Grade**: Full metadata tracking including model versions, uncertainty policies, and transformation parameters

## System Components

### 1. FastAPI Orchestration Server

The central control plane that:
- Manages job lifecycle and state transitions
- Coordinates AI service invocations
- Tracks artifacts and their lineage
- Provides REST API for clients
- Handles authentication and authorization

### 2. AI Services (Containerized)

Three specialized services that operate on the Symbolic IR:

- **OMR Service** (Phase 2): Converts PDF → Symbolic IR v1
- **Fingering AI Service** (Phase 3): Adds fingering annotations → Symbolic IR v2
- **Renderer Service** (Phase 4): Converts Symbolic IR → MusicXML/SVG/MIDI

Each service is containerized and can be scaled independently.

### 3. PostgreSQL Database

Stores:
- User accounts and authentication
- Job metadata and state
- Artifact metadata (not the actual files)
- Artifact lineage relationships
- Transformation history

### 4. MinIO Object Storage

S3-compatible storage for:
- PDF uploads
- Symbolic IR artifacts (JSON)
- Generated outputs (MusicXML, MIDI, SVG)
- All artifacts are immutable and versioned

### 5. Redis

Used for:
- Job queue management (future: Celery/RQ)
- Caching frequently accessed data
- Session management

## Data Flow

```
PDF Upload
    ↓
[FastAPI Server] → Store PDF as artifact
    ↓
Create Job (status: PENDING)
    ↓
[OMR Service] → PDF → Symbolic IR v1
    ↓
Store IR v1 artifact, record lineage
    ↓
[Fingering AI Service] → IR v1 → IR v2 (with fingering)
    ↓
Store IR v2 artifact, record lineage
    ↓
[Renderer Service] → IR v2 → MusicXML/SVG/MIDI
    ↓
Store output artifacts, record lineage
    ↓
Job Complete
```

## Symbolic IR Rationale

Why not direct PDF→MusicXML conversion?

1. **Modularity**: Each stage can be improved independently
2. **Research**: Symbolic IR allows experimentation with different models
3. **Traceability**: Full lineage from PDF to final output
4. **Flexibility**: Multiple output formats from same IR
5. **Quality Control**: Validate and inspect intermediate representations

## Job Lifecycle

### States

1. **PENDING** - Job created, waiting to start
2. **OMR_PROCESSING** - OMR service processing PDF
3. **OMR_COMPLETED** - OMR finished successfully
4. **OMR_FAILED** - OMR failed (can retry)
5. **FINGERING_PROCESSING** - Fingering AI processing IR
6. **FINGERING_COMPLETED** - Fingering finished successfully
7. **FINGERING_FAILED** - Fingering failed (can retry)
8. **RENDERING_PROCESSING** - Renderer generating outputs
9. **COMPLETED** - All stages complete
10. **FAILED** - Job failed irrecoverably

### State Transitions

Valid transitions are enforced by the state machine:
- PENDING → OMR_PROCESSING
- OMR_PROCESSING → OMR_COMPLETED | OMR_FAILED
- OMR_COMPLETED → FINGERING_PROCESSING
- FINGERING_PROCESSING → FINGERING_COMPLETED | FINGERING_FAILED
- FINGERING_COMPLETED → RENDERING_PROCESSING
- RENDERING_PROCESSING → COMPLETED | FAILED
- Any state → FAILED (on critical error)

## Artifact Versioning and Lineage

### Artifact Types

- `pdf` - Original uploaded PDF
- `ir_v1` - Symbolic IR after OMR
- `ir_v2` - Symbolic IR after fingering annotation
- `musicxml` - Final MusicXML export
- `midi` - MIDI export
- `svg` - SVG visualization

### Versioning Strategy

- Each artifact has a `schema_version` (e.g., "1.0.0")
- Multiple schema versions can coexist
- Artifacts are immutable (never updated, only new versions created)
- Full lineage tracked in `artifact_lineage` table

### Lineage Graph

```
PDF (artifact_1)
    ↓ [OMR transformation]
IR v1 (artifact_2)
    ↓ [Fingering transformation]
IR v2 (artifact_3)
    ↓ [Rendering transformation]
MusicXML (artifact_4)
MIDI (artifact_5)
SVG (artifact_6)
```

Each transformation records:
- Source artifact ID
- Derived artifact ID
- Transformation type
- Transformation version
- Timestamp

## Technology Choices

### FastAPI
- Modern async Python framework
- Automatic OpenAPI documentation
- Type hints and Pydantic validation
- High performance

### Async SQLAlchemy 2.0+
- Modern async/await syntax
- Type-safe queries
- Connection pooling
- Migration support via Alembic

### MinIO
- S3-compatible API
- Easy local development
- Production-ready (can switch to AWS S3)
- Bucket versioning support

### Pydantic v2
- Runtime type validation
- Settings management
- JSON schema generation
- Performance improvements

### structlog
- Structured JSON logging
- Request correlation IDs
- Production-ready logging
- Easy integration with log aggregation

## Security

- JWT-based authentication
- Bcrypt password hashing
- CORS configuration
- Input validation on all endpoints
- SQL injection prevention (SQLAlchemy ORM)
- File upload validation

## Scalability Considerations

- Stateless API server (horizontal scaling)
- Independent service containers
- Database connection pooling
- Redis for distributed caching
- Object storage for large files
- Async operations throughout

## Future Enhancements

- Celery/RQ for async job processing
- WebSocket support for real-time updates
- GraphQL API option
- Multi-tenant support
- Advanced caching strategies
- Metrics and monitoring (Prometheus/Grafana)


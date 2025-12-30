---
name: Symbolic IR Foundation
overview: Build the complete Symbolic Score Intermediate Representation (IR) v1 foundation, including Pydantic schemas, serialization utilities, storage integration, versioning system, and comprehensive test fixtures.
todos: []
---

# Phase 1: Symbolic IR Foundation Imp

lementation Plan

## Overview

Implement the complete Symbolic Score IR v1 system, which serves as the core data structure for the Étude pipeline. This IR decouples perception (OMR) from reasoning (fingering inference) from rendering (MusicXML export).

## Architecture

The IR system consists of:

- **Schema Layer**: Pydantic models organized by domain (notes, temporal, spatial, grouping, confidence, metadata)
- **Service Layer**: IR-specific service for storage/retrieval/validation
- **API Layer**: IR-specific endpoints for validation and management
- **Version Registry**: Schema version tracking and evolution support

## Implementation Tasks

### 1. Schema Structure Setup

Create directory structure:

- `server/app/schemas/symbolic_ir/__init__.py` - Package exports
- `server/app/schemas/symbolic_ir/v1/__init__.py` - V1 exports
- `server/app/schemas/symbolic_ir/v1/note.py` - Note event models
- `server/app/schemas/symbolic_ir/v1/temporal.py` - Time representation models
- `server/app/schemas/symbolic_ir/v1/spatial.py` - Staff/position models
- `server/app/schemas/symbolic_ir/v1/grouping.py` - Chord/voice grouping models
- `server/app/schemas/symbolic_ir/v1/confidence.py` - Uncertainty models
- `server/app/schemas/symbolic_ir/v1/metadata.py` - Document metadata models
- `server/app/schemas/symbolic_ir/v1/schema.py` - Top-level IR assembly
- `server/app/schemas/symbolic_ir/version_registry.py` - Schema version tracking

### 2. Core Schema Models

**Temporal Models** (`temporal.py`):

- `TemporalPosition`: Dual time representation (seconds + metric beats)
- `Duration`: Duration in both continuous and metric representations
- Custom Pydantic serializer for `Fraction` using `fractions.Fraction` with string serialization (e.g., "5/4")

**Spatial Models** (`spatial.py`):

- `SpatialPosition`: Staff-relative position from OMR
- `BoundingBox`: Page coordinate bounding box

**Note Models** (`note.py`):

- `PitchRepresentation`: Multiple pitch representations (MIDI, pitch class, scientific notation, frequency)
- `NoteEvent`: Complete atomic note event with all attributes

**Grouping Models** (`grouping.py`):

- `ChordMembership`: Probabilistic chord membership
- `VoiceAssignment`: Probabilistic voice assignment with alternatives
- `HandAssignment`: Probabilistic hand assignment with alternatives
- `VoiceAlternative` / `HandAlternative`: Alternative assignments
- `ChordGroup`: Top-level chord grouping structure
- `Voice`: Voice structure definition

**Confidence Models** (`confidence.py`):

- `NoteConfidence`: Multi-level confidence scores with validation

**Metadata Models** (`metadata.py`):

- `IRMetadata`: Complete provenance and metadata
- `GenerationMetadata`: Service/model generation info
- `LowConfidenceRegion`: Regions with low confidence

**Supporting Models** (`schema.py`):

- `TimeSignature` / `TimeSignatureChange`: Time signature with changes
- `KeySignature`: Key signature (fifths + mode)
- `Tempo` / `TempoChange`: Tempo with changes
- `Staff`: Staff configuration

**Top-Level Schema** (`schema.py`):

- `SymbolicScoreIR`: Complete IR with:
- All note events, chords, voices
- Internal indices (`_note_by_id`, `_notes_by_staff`, `_notes_by_time`)
- Accessor methods (`get_note_by_id`, `get_notes_by_staff`, `get_notes_in_time_range`, etc.)
- JSON serialization methods (`to_json`, `from_json`)

### 3. Version Registry

**Version Registry** (`version_registry.py`):

- `IRSchemaVersion`: Enum of schema versions
- `SchemaRegistry`: Registry class for schema version tracking
- Register v1.0.0 schema on import
- Version compatibility checking using `packaging` library

**Dependencies**: Add `packaging>=23.0` to `requirements.txt`

### 4. IR Service

**IR Service** (`server/app/services/ir_service.py`):

- `IRService`: Specialized service for IR management
- Methods:
- `store_ir()`: Serialize, validate, store IR as artifact with proper metadata
- `load_ir()`: Load IR from storage, validate checksum, deserialize
- `validate_ir()`: Validate IR data against schema
- `get_ir_by_job()`: Get most recent IR of specific type for a job
- Integration with existing `ArtifactService` and `StorageService`
- Proper artifact metadata extraction from IR
- Lineage tracking for IR artifacts

### 5. API Endpoints

**IR API** (`server/app/api/v1/ir.py`):

- `POST /api/v1/ir/validate`: Validate IR data without storing
- `GET /api/v1/ir/{artifact_id}`: Get IR by artifact ID (deserialized)
- `POST /api/v1/ir/jobs/{job_id}`: Store new IR for a job
- `GET /api/v1/ir/jobs/{job_id}`: Get latest IR for a job

**Router Registration**: Add IR router to `server/app/api/v1/__init__.py`**Dependencies**: Add dependency function `get_ir_service()` in `server/app/dependencies.py`

### 6. Test Fixtures

**Test Fixtures** (`server/tests/fixtures/symbolic_ir/`):

- `minimal_ir_v1.json`: Minimal IR covering all required fields
- `realistic_ir_v1.json`: Complete realistic example (Chopin Nocturne excerpt)
- `pytest` fixtures in `server/tests/conftest.py`:
- `minimal_ir_v1()`: Load minimal IR fixture
- `realistic_ir_v1()`: Load realistic IR fixture
- `ir_service()`: IRService instance fixture

**Test Cases** (`server/tests/test_symbolic_ir/`):

- `test_schemas.py`: Schema validation tests
- `test_serialization.py`: JSON serialization/deserialization tests
- `test_ir_service.py`: IR service integration tests
- `test_api.py`: API endpoint tests

### 7. Integration Points

**Artifact Model Alignment**:

- Use `artifact_metadata` field (not `metadata`) for artifact storage
- Map IR metadata to artifact metadata appropriately
- Ensure `ArtifactType.IR_V1` is used correctly

**Storage Path Structure**:

- Use `jobs/{job_id}/ir/v1/{artifact_id}.json` for IR storage
- Align with existing `ArtifactService` patterns

## Key Implementation Details

1. **Fraction Serialization**: Custom Pydantic serializer that converts `Fraction` to string format ("5/4") in JSON, and parses back to `Fraction` on deserialization
2. **Private Attributes**: Use `PrivateAttr` for internal indices (`_note_by_id`, etc.) that are excluded from JSON serialization
3. **Model Validators**: Implement validators for:

- `NoteConfidence`: Ensure overall confidence doesn't exceed max component
- `SymbolicScoreIR`: Build indices after model validation

4. **Error Handling**: Proper validation errors, checksum verification, and schema version compatibility checks
5. **Type Safety**: Full type hints throughout, leveraging Pydantic 2.5+ features

## Files to Create/Modify

**New Files** (15):

- Schema files (9 files in `schemas/symbolic_ir/`)
- `services/ir_service.py`
- `api/v1/ir.py`
- Test fixtures (2 JSON files)
- Test files (3 test modules)

**Modified Files** (4):

- `requirements.txt` - Add `packaging`
- `app/api/v1/__init__.py` - Add IR router
- `app/dependencies.py` - Add `get_ir_service()`
- `tests/conftest.py` - Add IR fixtures

## Validation Strategy

- Schema validation via Pydantic
- JSON schema generation for documentation
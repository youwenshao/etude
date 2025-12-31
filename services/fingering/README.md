# Fingering AI Service

The Fingering AI Service is the **intelligence layer** of Étude, using the PRamoneda/Automatic-Piano-Fingering model (ArLSTM/ArGNN) to infer optimal piano fingering from Symbolic IR v1.

## Overview

This service:
- Takes Symbolic IR v1 (from OMR) as input
- Applies uncertainty policies to resolve hand/voice assignments
- Extracts features and runs ML inference
- Produces IR v2 with fingering annotations

## Architecture

```
IR v1 → IR-to-Model Adapter → Model Inference → Model-to-IR Adapter → IR v2
```

## Features

- **Model Support**: ArLSTM and ArGNN architectures
- **Uncertainty Handling**: MLE policy for resolving probabilistic assignments
- **Conditional Loading**: Works with or without pretrained weights (graceful degradation)
- **Hand Separation**: Automatic left/right hand detection
- **Feature Extraction**: Pitch, duration, IOI, metric position, chord info

## API Endpoints

- `GET /health` - Health check
- `GET /info` - Service metadata
- `POST /infer` - Infer fingering for IR v1, returns IR v2

## Configuration

Environment variables:
- `FINGERING_MODEL_TYPE` - Model architecture: `arlstm` or `argnn` (default: `arlstm`)
- `FINGERING_ARLSTM_MODEL_PATH` - Path to ArLSTM weights
- `FINGERING_ARGNN_MODEL_PATH` - Path to ArGNN weights
- `FINGERING_DEVICE` - Device: `cpu`, `cuda`, or `mps` (auto-detected)
- `FINGERING_DEFAULT_POLICY` - Uncertainty policy: `mle` or `sampling` (default: `mle`)

## Development

The service works without model weights for development. It will use a placeholder model that returns dummy predictions.

## Testing

```bash
pytest tests/
```

## Model Weights

Model weights should be placed in:
- `/app/models/arlstm/best_model.pt` for ArLSTM
- `/app/models/argnn/best_model.pt` for ArGNN

Or mounted as volumes in Docker.


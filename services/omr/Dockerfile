FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Optional: CUDA support for GPU inference
# FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
# ... additional CUDA setup if needed

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Polyphonic-TrOMR repository
COPY Polyphonic-TrOMR/ ./Polyphonic-TrOMR/

# Set PYTHONPATH to include Polyphonic-TrOMR
ENV PYTHONPATH=/app/Polyphonic-TrOMR:$PYTHONPATH

# Copy application code
COPY app/ ./app/

# Create directory for model weights
RUN mkdir -p /app/models

# Note: Model weights should be available in Polyphonic-TrOMR/tromr/workspace/checkpoints/
# or mounted as a volume at runtime

# Expose API port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the API server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

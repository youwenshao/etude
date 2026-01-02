FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    pkg-config \
    libssl-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Rust using rustup (use older version compatible with tokenizers for transformers 4.20.1)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    export PATH="$HOME/.cargo/bin:$PATH" && \
    rustup toolchain install 1.70.0 && \
    rustup default 1.70.0 && \
    rustup --version && cargo --version

# Optional: CUDA support for GPU inference
# FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
# ... additional CUDA setup if needed

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
ENV PATH="/root/.cargo/bin:${PATH}"
# Allow unsafe reference casting for tokenizers (needed for transformers 4.20.1)
ENV RUSTFLAGS="-A invalid_reference_casting"
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy Polyphonic-TrOMR repository
COPY Polyphonic-TrOMR/ ./Polyphonic-TrOMR/

# Set PYTHONPATH to include Polyphonic-TrOMR and its tromr subdirectory
ENV PYTHONPATH=/app/Polyphonic-TrOMR:/app/Polyphonic-TrOMR/tromr:$PYTHONPATH

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

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
# Install torch first, then torch-scatter and torch-sparse (which need torch at build time)
# Then install the rest of the requirements (pip will skip already-installed packages)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir torch==2.1.0 numpy==1.24.3 && \
    pip install --no-cache-dir --no-build-isolation torch-scatter==2.1.2 torch-sparse==0.6.18 && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy/link to PRamoneda model code
COPY Automatic-Piano-Fingering/ ./Automatic-Piano-Fingering/

# Set PYTHONPATH to include PRamoneda model
ENV PYTHONPATH=/app/Automatic-Piano-Fingering:$PYTHONPATH

# Create directory for model weights
RUN mkdir -p /app/models/arlstm
RUN mkdir -p /app/models/argnn

# Note: Model weights should be downloaded from the model repository
# or mounted as a volume at runtime

# Expose API port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the API server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]

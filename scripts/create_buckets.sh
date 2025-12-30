#!/bin/sh
# Script to create MinIO buckets on container startup
# This is mounted into the MinIO container

set -e

# Wait for MinIO to be ready
until mc alias set myminio http://localhost:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} 2>/dev/null; do
  echo "Waiting for MinIO to be ready..."
  sleep 2
done

# Create buckets
mc mb myminio/etude-artifacts --ignore-existing || true
mc mb myminio/etude-pdfs --ignore-existing || true

echo "MinIO buckets created successfully"


#!/bin/bash

# Étude local development setup script

set -e

echo "🚀 Setting up Étude development environment..."

# Check Docker
# First, try to find docker in common locations if not in PATH
if ! command -v docker &> /dev/null; then
    if [ -f "/Applications/Docker.app/Contents/Resources/bin/docker" ]; then
        # Docker Desktop on macOS might not be in PATH
        export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
    elif [ -f "/usr/local/bin/docker" ]; then
        export PATH="/usr/local/bin:$PATH"
    fi
fi

# Check if docker command is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop first."
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is installed but the Docker daemon is not running."
    echo "   Please start Docker Desktop and try again."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Function to check if a port is in use
check_port() {
    local port=$1
    local service=$2
    # Try lsof first (works on macOS and Linux)
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "❌ Port $port is already in use (required for $service)."
        echo "   Please stop the service using this port or change the port mapping in docker-compose.yml"
        echo ""
        echo "   To find what's using the port, run:"
        echo "   lsof -i :$port"
        return 1
    fi
    # Fallback: try netcat if available
    if command -v nc &> /dev/null && nc -z localhost $port 2>/dev/null; then
        echo "❌ Port $port is already in use (required for $service)."
        echo "   Please stop the service using this port or change the port mapping in docker-compose.yml"
        return 1
    fi
    return 0
}

# Check required ports
echo "🔍 Checking if required ports are available..."
PORT_ERROR=0
check_port 5432 "PostgreSQL" || PORT_ERROR=1
check_port 9000 "MinIO API" || PORT_ERROR=1
check_port 9001 "MinIO Console" || PORT_ERROR=1
check_port 6379 "Redis" || PORT_ERROR=1
check_port 8000 "FastAPI Server" || PORT_ERROR=1

if [ $PORT_ERROR -eq 1 ]; then
    echo ""
    echo "💡 Tip: If you have existing Docker containers using these ports, you can stop them with:"
    echo "   docker ps"
    echo "   docker stop <container_id>"
    echo ""
    echo "   Or stop all Étude containers with:"
    echo "   docker stop etude_postgres etude_minio etude_redis etude_server 2>/dev/null || true"
    exit 1
fi
echo "✅ All required ports are available"

# Check for existing containers that might conflict
echo "🔍 Checking for existing containers..."
EXISTING_CONTAINERS=$(docker ps -a --filter "name=etude_" --format "{{.Names}}" 2>/dev/null || true)
if [ -n "$EXISTING_CONTAINERS" ]; then
    echo "⚠️  Found existing Étude containers:"
    echo "$EXISTING_CONTAINERS" | while read container; do
        echo "   - $container"
    done
    echo ""
    echo "   These will be recreated when starting services."
fi

# Create .env from .env.example if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please review and update if needed."
else
    echo "ℹ️  .env file already exists, skipping..."
fi

# Start services
echo "🐳 Starting Docker services..."
if command -v docker-compose &> /dev/null; then
    if ! docker-compose up -d; then
        echo ""
        echo "❌ Failed to start Docker services."
        echo "   This might be due to port conflicts or other issues."
        echo "   Check the error messages above for details."
        exit 1
    fi
else
    if ! docker compose up -d; then
        echo ""
        echo "❌ Failed to start Docker services."
        echo "   This might be due to port conflicts or other issues."
        echo "   Check the error messages above for details."
        exit 1
    fi
fi

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check PostgreSQL
echo "🔍 Checking PostgreSQL..."
until docker exec etude_postgres pg_isready -U etude > /dev/null 2>&1; do
    echo "   Waiting for PostgreSQL..."
    sleep 2
done
echo "✅ PostgreSQL is ready"

# Check MinIO
echo "🔍 Checking MinIO..."
until curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; do
    echo "   Waiting for MinIO..."
    sleep 2
done
echo "✅ MinIO is ready"

# Check Redis
echo "🔍 Checking Redis..."
until docker exec etude_redis redis-cli ping > /dev/null 2>&1; do
    echo "   Waiting for Redis..."
    sleep 2
done
echo "✅ Redis is ready"

# Run migrations
echo "📊 Running database migrations..."
cd server
if command -v docker-compose &> /dev/null; then
    docker-compose exec -T server alembic upgrade head || docker exec etude_server alembic upgrade head
else
    docker compose exec -T server alembic upgrade head || docker exec etude_server alembic upgrade head
fi
cd ..
echo "✅ Migrations completed"

# Create MinIO buckets (if not already created)
echo "🪣 Ensuring MinIO buckets exist..."
docker exec etude_minio mc alias set myminio http://localhost:9000 minioadmin minioadmin123 2>/dev/null || true
docker exec etude_minio mc mb myminio/etude-artifacts --ignore-existing 2>/dev/null || true
docker exec etude_minio mc mb myminio/etude-pdfs --ignore-existing 2>/dev/null || true
echo "✅ MinIO buckets ready"

# Check if user wants to seed database
if [ "$1" == "--seed" ]; then
    echo "🌱 Seeding database..."
    cd server
    python ../scripts/seed_db.py || docker exec etude_server python ../scripts/seed_db.py
    cd ..
    echo "✅ Database seeded"
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "📋 Service URLs:"
echo "   - FastAPI Server: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - MinIO Console: http://localhost:9001 (minioadmin/minioadmin123)"
echo "   - PostgreSQL: localhost:5432"
echo ""
echo "📝 Next steps:"
echo "   1. Review .env file and update if needed"
echo "   2. Visit http://localhost:8000/docs to explore the API"
echo "   3. Run tests: cd server && pytest"
echo ""


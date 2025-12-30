# Étude

A research-grade pipeline that converts scanned sheet music (PDF) into accurate piano fingering annotations using symbolic intermediate representations and pretrained ML models.

## Architecture

Étude is a multi-stage system with:

- **FastAPI backend** - Orchestration and control plane
- **Multiple AI services** - OMR, Fingering AI, Renderer (each containerized)
- **PostgreSQL** - Metadata and job tracking
- **Object storage** - MinIO for local dev (S3-compatible) for artifacts
- **Flutter client** - To be built in later phases

This system is NOT an end-to-end PDF→MusicXML converter. It's a **symbolic-first reasoning pipeline** where all ML operates on a custom Symbolic Score IR (Intermediate Representation), with MusicXML only as a final export format.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd etude
```

2. Run the setup script:
```bash
./scripts/setup_local.sh
```

This script will:
- Check Docker installation
- Create `.env` from `.env.example`
- Start all services (PostgreSQL, MinIO, Redis, FastAPI server)
- Wait for services to be healthy
- Run database migrations
- Create MinIO buckets
- Optionally seed the database

3. Access the services:
- FastAPI server: http://localhost:8000
- API documentation: http://localhost:8000/docs
- MinIO console: http://localhost:9001 (minioadmin/minioadmin123)
- PostgreSQL: localhost:5432

## Development

### Running Services

Start all services:
```bash
docker-compose up -d
```

View logs:
```bash
docker-compose logs -f server
```

Stop all services:
```bash
docker-compose down
```

### Database Migrations

Create a new migration:
```bash
cd server
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

### Running Tests

```bash
cd server
pytest
```

With coverage:
```bash
pytest --cov=app --cov-report=html
```

### Local Development (without Docker)

1. Start PostgreSQL, MinIO, and Redis using Docker Compose:
```bash
docker-compose up -d postgres minio redis
```

2. Create a virtual environment:
```bash
cd server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp ../.env.example ../.env
# Edit .env with local connection strings
```

5. Run migrations:
```bash
alembic upgrade head
```

6. Start the server:
```bash
uvicorn app.main:app --reload
```

## Project Structure

```
etude/
├── docker-compose.yml      # Local development services
├── .env.example            # Environment variable template
├── README.md               # This file
├── docs/                   # Documentation
│   └── architecture.md     # System architecture details
├── server/                 # FastAPI orchestration server
│   ├── app/                # Application code
│   ├── alembic/            # Database migrations
│   └── tests/              # Test suite
├── services/               # AI service containers
│   ├── omr/                # OMR service (Phase 2)
│   ├── fingering/          # Fingering AI service (Phase 3)
│   └── renderer/           # Renderer service (Phase 4)
├── client/                 # Flutter app (Phase 5+)
└── scripts/                # Utility scripts
    ├── setup_local.sh      # Local setup automation
    └── seed_db.py          # Database seeding
```

## Technology Stack

- **Backend**: FastAPI, Python 3.11+
- **Database**: PostgreSQL 15 with async SQLAlchemy 2.0+
- **Object Storage**: MinIO (S3-compatible)
- **Cache/Queue**: Redis 7
- **Authentication**: JWT with passlib/bcrypt
- **Validation**: Pydantic v2
- **Migrations**: Alembic
- **Logging**: structlog
- **Testing**: pytest, pytest-asyncio

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Common Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Run migrations
cd server && alembic upgrade head

# Run tests
cd server && pytest

# Seed database
python scripts/seed_db.py

# Format code
cd server && black app tests

# Type checking
cd server && mypy app
```

## License

[License information]

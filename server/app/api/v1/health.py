"""Health check endpoints."""

import asyncio
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.db.session import engine
from app.services.storage_service import storage_service
from app.config import settings

router = APIRouter()


async def check_database() -> dict[str, Any]:
    """Check database connectivity."""
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "message": "Database connection successful"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


async def check_minio() -> dict[str, Any]:
    """Check MinIO connectivity."""
    try:
        # Try to list buckets
        async with storage_service._get_client() as s3:
            await s3.list_buckets()
        return {"status": "healthy", "message": "MinIO connection successful"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


async def check_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    try:
        import redis.asyncio as redis

        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.close()
        return {"status": "healthy", "message": "Redis connection successful"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


@router.get("", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "healthy"}


@router.get("/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check() -> dict[str, Any]:
    """Detailed health check with component status."""
    db_status, minio_status, redis_status = await asyncio.gather(
        check_database(),
        check_minio(),
        check_redis(),
    )

    all_healthy = all(
        [
            db_status["status"] == "healthy",
            minio_status["status"] == "healthy",
            redis_status["status"] == "healthy",
        ]
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "components": {
            "database": db_status,
            "minio": minio_status,
            "redis": redis_status,
        },
    }


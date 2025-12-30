"""Database session management with async SQLAlchemy."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.config import settings

# Determine if we're using SQLite (for tests or local dev)
is_sqlite = "sqlite" in settings.DATABASE_URL.lower()

# Create async engine with appropriate pool settings
engine_kwargs = {
    "url": settings.DATABASE_URL,
    "echo": settings.ENVIRONMENT == "development",
    "pool_pre_ping": True,
}

# SQLite doesn't support pool_size/max_overflow, use StaticPool for in-memory
if is_sqlite:
    engine_kwargs["poolclass"] = StaticPool
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # For PostgreSQL and other databases, use connection pooling
    if settings.ENVIRONMENT == "test":
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

engine = create_async_engine(**engine_kwargs)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


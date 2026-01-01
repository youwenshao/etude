"""Pytest configuration and fixtures."""

import pytest
import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.core.security import get_password_hash


# Test database URL (use in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def minimal_ir_v1() -> dict:
    """Load minimal IR fixture."""
    import json
    from pathlib import Path

    fixture_path = Path(__file__).parent / "tests" / "fixtures" / "symbolic_ir" / "minimal_ir_v1.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def realistic_ir_v1() -> dict:
    """Load realistic IR fixture."""
    import json
    from pathlib import Path

    fixture_path = Path(__file__).parent / "tests" / "fixtures" / "symbolic_ir" / "realistic_ir_v1.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
async def ir_service(db_session: AsyncSession):
    """Create IR service instance."""
    from app.services.ir_service import IRService
    return IRService(db_session)


@pytest.fixture
def minimal_ir_v2(minimal_ir_v1) -> dict:
    """Create minimal IR v2 from IR v1."""
    ir_v2_data = minimal_ir_v1.copy()
    ir_v2_data["version"] = "2.0.0"
    ir_v2_data["fingering_metadata"] = {
        "model_name": "PRamoneda-ArLSTM",
        "model_version": "1.0.0",
        "ir_to_model_adapter_version": "1.0.0",
        "model_to_ir_adapter_version": "1.0.0",
        "uncertainty_policy": "mle",
        "notes_annotated": len(ir_v2_data.get("notes", [])),
        "total_notes": len(ir_v2_data.get("notes", [])),
        "coverage": 1.0 if len(ir_v2_data.get("notes", [])) > 0 else 0.0,
    }
    
    # Add fingering to notes if they exist
    if ir_v2_data.get("notes"):
        for note in ir_v2_data["notes"]:
            note["fingering"] = {
                "finger": 1,
                "hand": "right",
                "confidence": 0.95,
                "alternatives": [],
                "uncertainty_policy": "mle",
                "model_name": "PRamoneda-ArLSTM",
                "model_version": "1.0.0",
                "adapter_version": "1.0.0",
            }
    
    return ir_v2_data


@pytest.fixture
def test_pdf_bytes() -> bytes:
    """Create minimal PDF content for testing."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n9\n%%EOF"


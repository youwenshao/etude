"""Database seeding script for development."""

import asyncio
import sys
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.user import User
from app.models.job import Job, JobStatus, JobStage
from app.models.artifact import Artifact, ArtifactType
from app.models.artifact_lineage import ArtifactLineage
from app.core.security import get_password_hash
from app.services.storage_service import storage_service
import hashlib
from datetime import datetime
import uuid


async def seed_database():
    """Seed the database with test data."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create test users
        print("Creating test users...")
        
        # Check if users already exist
        result = await session.execute(select(User).where(User.email == "admin@etude.test"))
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            admin_user = User(
                email="admin@etude.test",
                hashed_password=get_password_hash("admin123"),
                full_name="Admin User",
                is_active=True,
            )
            session.add(admin_user)
            await session.flush()
            print(f"  ✓ Created admin user: {admin_user.email}")
        else:
            print(f"  ℹ Admin user already exists: {admin_user.email}")

        result = await session.execute(select(User).where(User.email == "user@etude.test"))
        test_user = result.scalar_one_or_none()
        
        if not test_user:
            test_user = User(
                email="user@etude.test",
                hashed_password=get_password_hash("user123"),
                full_name="Test User",
                is_active=True,
            )
            session.add(test_user)
            await session.flush()
            print(f"  ✓ Created test user: {test_user.email}")
        else:
            print(f"  ℹ Test user already exists: {test_user.email}")

        await session.commit()

        # Create sample jobs
        print("\nCreating sample jobs...")
        
        # Job 1: Pending
        job1 = Job(
            user_id=test_user.id,
            status=JobStatus.PENDING.value,
            stage=JobStage.OMR.value,
            metadata={"filename": "sample1.pdf", "created_at": datetime.utcnow().isoformat()},
        )
        session.add(job1)
        await session.flush()
        print(f"  ✓ Created job: {job1.id} (status: {job1.status})")

        # Job 2: OMR Processing
        job2 = Job(
            user_id=test_user.id,
            status=JobStatus.OMR_PROCESSING.value,
            stage=JobStage.OMR.value,
            metadata={"filename": "sample2.pdf", "created_at": datetime.utcnow().isoformat()},
        )
        session.add(job2)
        await session.flush()
        print(f"  ✓ Created job: {job2.id} (status: {job2.status})")

        # Job 3: Completed
        job3 = Job(
            user_id=test_user.id,
            status=JobStatus.COMPLETED.value,
            stage=JobStage.RENDERING.value,
            completed_at=datetime.utcnow(),
            metadata={
                "filename": "sample3.pdf",
                "created_at": datetime.utcnow().isoformat(),
                "transitions": [
                    {"from": "pending", "to": "omr_processing", "timestamp": datetime.utcnow().isoformat()},
                    {"from": "omr_processing", "to": "omr_completed", "timestamp": datetime.utcnow().isoformat()},
                ],
            },
        )
        session.add(job3)
        await session.flush()
        print(f"  ✓ Created job: {job3.id} (status: {job3.status})")

        # Job 4: Failed
        job4 = Job(
            user_id=test_user.id,
            status=JobStatus.FAILED.value,
            stage=JobStage.OMR.value,
            completed_at=datetime.utcnow(),
            error_message="OMR processing failed: Unable to detect staff lines",
            metadata={"filename": "sample4.pdf", "created_at": datetime.utcnow().isoformat()},
        )
        session.add(job4)
        await session.flush()
        print(f"  ✓ Created job: {job4.id} (status: {job4.status})")

        await session.commit()

        # Create sample artifacts for job3 (completed job)
        print("\nCreating sample artifacts...")
        
        # PDF artifact
        pdf_data = b"Mock PDF content for testing"
        pdf_checksum = hashlib.sha256(pdf_data).hexdigest()
        pdf_key = f"jobs/{job3.id}/artifacts/{job3.id}_pdf.pdf"
        
        try:
            await storage_service.upload_file(
                pdf_data, pdf_key, settings.MINIO_BUCKET_PDFS, content_type="application/pdf"
            )
        except Exception as e:
            print(f"  ⚠ Warning: Could not upload PDF to storage: {e}")
        
        pdf_artifact = Artifact(
            job_id=job3.id,
            artifact_type=ArtifactType.PDF.value,
            schema_version="1.0.0",
            storage_path=pdf_key,
            file_size=len(pdf_data),
            checksum=pdf_checksum,
            metadata={"filename": "sample3.pdf", "original_upload": True},
        )
        session.add(pdf_artifact)
        await session.flush()
        print(f"  ✓ Created PDF artifact: {pdf_artifact.id}")

        # IR v1 artifact
        ir_v1_data = b'{"version": "1.0.0", "measures": []}'
        ir_v1_checksum = hashlib.sha256(ir_v1_data).hexdigest()
        ir_v1_key = f"jobs/{job3.id}/artifacts/{uuid.uuid4()}.json"
        
        try:
            await storage_service.upload_file(
                ir_v1_data, ir_v1_key, settings.MINIO_BUCKET_ARTIFACTS, content_type="application/json"
            )
        except Exception as e:
            print(f"  ⚠ Warning: Could not upload IR v1 to storage: {e}")
        
        ir_v1_artifact = Artifact(
            job_id=job3.id,
            artifact_type=ArtifactType.IR_V1.value,
            schema_version="1.0.0",
            storage_path=ir_v1_key,
            file_size=len(ir_v1_data),
            checksum=ir_v1_checksum,
            metadata={"model_version": "OMR-v1.0.0", "transformation": "omr"},
            parent_artifact_id=pdf_artifact.id,
        )
        session.add(ir_v1_artifact)
        await session.flush()
        print(f"  ✓ Created IR v1 artifact: {ir_v1_artifact.id}")

        # IR v2 artifact (with fingering)
        ir_v2_data = b'{"version": "2.0.0", "measures": [], "fingering": {}}'
        ir_v2_checksum = hashlib.sha256(ir_v2_data).hexdigest()
        ir_v2_key = f"jobs/{job3.id}/artifacts/{uuid.uuid4()}.json"
        
        try:
            await storage_service.upload_file(
                ir_v2_data, ir_v2_key, settings.MINIO_BUCKET_ARTIFACTS, content_type="application/json"
            )
        except Exception as e:
            print(f"  ⚠ Warning: Could not upload IR v2 to storage: {e}")
        
        ir_v2_artifact = Artifact(
            job_id=job3.id,
            artifact_type=ArtifactType.IR_V2.value,
            schema_version="2.0.0",
            storage_path=ir_v2_key,
            file_size=len(ir_v2_data),
            checksum=ir_v2_checksum,
            metadata={"model_version": "PRamoneda-ArLSTM-v1.2.3", "transformation": "fingering_inference"},
            parent_artifact_id=ir_v1_artifact.id,
        )
        session.add(ir_v2_artifact)
        await session.flush()
        print(f"  ✓ Created IR v2 artifact: {ir_v2_artifact.id}")

        # MusicXML artifact
        musicxml_data = b'<?xml version="1.0"?><score-partwise/>'
        musicxml_checksum = hashlib.sha256(musicxml_data).hexdigest()
        musicxml_key = f"jobs/{job3.id}/artifacts/{uuid.uuid4()}.musicxml"
        
        try:
            await storage_service.upload_file(
                musicxml_data, musicxml_key, settings.MINIO_BUCKET_ARTIFACTS, content_type="application/xml"
            )
        except Exception as e:
            print(f"  ⚠ Warning: Could not upload MusicXML to storage: {e}")
        
        musicxml_artifact = Artifact(
            job_id=job3.id,
            artifact_type=ArtifactType.MUSICXML.value,
            schema_version="1.0.0",
            storage_path=musicxml_key,
            file_size=len(musicxml_data),
            checksum=musicxml_checksum,
            metadata={"transformation": "rendering", "format": "musicxml"},
            parent_artifact_id=ir_v2_artifact.id,
        )
        session.add(musicxml_artifact)
        await session.flush()
        print(f"  ✓ Created MusicXML artifact: {musicxml_artifact.id}")

        # Create lineage records
        lineage1 = ArtifactLineage(
            source_artifact_id=pdf_artifact.id,
            derived_artifact_id=ir_v1_artifact.id,
            transformation_type="omr",
            transformation_version="1.0.0",
        )
        session.add(lineage1)

        lineage2 = ArtifactLineage(
            source_artifact_id=ir_v1_artifact.id,
            derived_artifact_id=ir_v2_artifact.id,
            transformation_type="fingering_inference",
            transformation_version="1.2.3",
        )
        session.add(lineage2)

        lineage3 = ArtifactLineage(
            source_artifact_id=ir_v2_artifact.id,
            derived_artifact_id=musicxml_artifact.id,
            transformation_type="rendering",
            transformation_version="1.0.0",
        )
        session.add(lineage3)

        await session.commit()
        print(f"  ✓ Created lineage records")

        print("\n✅ Database seeding completed!")
        print("\n📋 Test credentials:")
        print("   Admin: admin@etude.test / admin123")
        print("   User:  user@etude.test / user123")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())


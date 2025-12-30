"""Storage service for MinIO/S3 operations."""

from typing import Any

import aioboto3
from botocore.exceptions import ClientError

from app.config import settings


class StorageService:
    """Service for object storage operations using S3-compatible API."""

    def __init__(self) -> None:
        """Initialize storage service."""
        self.endpoint_url = (
            f"https://{settings.MINIO_ENDPOINT}"
            if settings.MINIO_USE_SSL
            else f"http://{settings.MINIO_ENDPOINT}"
        )
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.session = aioboto3.Session()

    async def _get_client(self):
        """Get S3 client."""
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="us-east-1",  # MinIO doesn't care about region
        )

    async def ensure_bucket_exists(self, bucket_name: str) -> None:
        """Ensure a bucket exists, create if it doesn't."""
        async with await self._get_client() as s3:
            try:
                await s3.head_bucket(Bucket=bucket_name)
            except ClientError:
                # Bucket doesn't exist, create it
                await s3.create_bucket(Bucket=bucket_name)

    async def upload_file(
        self, file: bytes, key: str, bucket: str, content_type: str | None = None
    ) -> str:
        """
        Upload a file to object storage.

        Args:
            file: File content as bytes
            key: Storage key/path
            bucket: Bucket name
            content_type: Optional content type

        Returns:
            Storage path (bucket/key)
        """
        async with await self._get_client() as s3:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            await s3.put_object(Bucket=bucket, Key=key, Body=file, **extra_args)
            return f"{bucket}/{key}"

    async def download_file(self, key: str, bucket: str) -> bytes:
        """
        Download a file from object storage.

        Args:
            key: Storage key/path
            bucket: Bucket name

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        async with await self._get_client() as s3:
            try:
                response = await s3.get_object(Bucket=bucket, Key=key)
                async with response["Body"] as stream:
                    return await stream.read()
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    raise FileNotFoundError(f"File not found: {bucket}/{key}")
                raise

    async def delete_file(self, key: str, bucket: str) -> bool:
        """
        Delete a file from object storage.

        Args:
            key: Storage key/path
            bucket: Bucket name

        Returns:
            True if deleted, False if not found
        """
        async with await self._get_client() as s3:
            try:
                await s3.delete_object(Bucket=bucket, Key=key)
                return True
            except ClientError:
                return False

    async def generate_presigned_url(
        self, key: str, bucket: str, expiration: int = 3600
    ) -> str:
        """
        Generate a presigned URL for temporary access.

        Args:
            key: Storage key/path
            bucket: Bucket name
            expiration: Expiration time in seconds

        Returns:
            Presigned URL
        """
        async with await self._get_client() as s3:
            url = await s3.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expiration
            )
            return url

    async def get_file_metadata(self, key: str, bucket: str) -> dict[str, Any]:
        """
        Get file metadata from object storage.

        Args:
            key: Storage key/path
            bucket: Bucket name

        Returns:
            Dictionary with metadata (size, etag, content_type, etc.)

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        async with await self._get_client() as s3:
            try:
                response = await s3.head_object(Bucket=bucket, Key=key)
                return {
                    "size": response.get("ContentLength", 0),
                    "etag": response.get("ETag", "").strip('"'),
                    "content_type": response.get("ContentType", ""),
                    "last_modified": response.get("LastModified"),
                }
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    raise FileNotFoundError(f"File not found: {bucket}/{key}")
                raise


# Global instance
storage_service = StorageService()


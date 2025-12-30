"""API schemas for OMR service."""

from app.schemas.request import OMRProcessRequest
from app.schemas.response import OMRProcessResponse, ServiceInfo

__all__ = ["OMRProcessRequest", "OMRProcessResponse", "ServiceInfo"]


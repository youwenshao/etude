"""Request schemas for fingering service API."""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class FingeringRequest(BaseModel):
    """Request schema for fingering inference endpoint."""

    ir_v1: Dict[str, Any] = Field(
        ..., description="Symbolic Score IR v1 as dictionary"
    )
    uncertainty_policy: Optional[Literal["mle", "sampling"]] = Field(
        default="mle", description="Uncertainty handling policy"
    )


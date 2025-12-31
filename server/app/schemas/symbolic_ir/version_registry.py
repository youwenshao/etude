"""Schema version registry for Symbolic Score IR."""

from enum import Enum
from typing import Dict, Type

from pydantic import BaseModel
from packaging import version as pkg_version

from app.schemas.symbolic_ir.v1.schema import SymbolicScoreIR
from app.schemas.symbolic_ir.v2.schema import SymbolicScoreIRV2


class IRSchemaVersion(str, Enum):
    """Enumeration of all IR schema versions."""

    V1_0_0 = "1.0.0"
    V2_0_0 = "2.0.0"
    # Future versions will be added here
    # V1_1_0 = "1.1.0"


class SchemaRegistry:
    """
    Registry of IR schema versions.
    Enables loading and validating IRs from different schema versions.
    """

    _schemas: Dict[str, Type[BaseModel]] = {}

    @classmethod
    def register(cls, version: str, schema_class: Type[BaseModel]) -> None:
        """Register a schema version."""
        cls._schemas[version] = schema_class

    @classmethod
    def get_schema(cls, version: str) -> Type[BaseModel]:
        """Get schema class for a specific version."""
        if version not in cls._schemas:
            raise ValueError(f"Unknown IR schema version: {version}")
        return cls._schemas[version]

    @classmethod
    def get_latest_version(cls) -> str:
        """Get the latest schema version."""
        return IRSchemaVersion.V2_0_0.value

    @classmethod
    def is_compatible(cls, version: str, min_version: str) -> bool:
        """Check if a version is compatible with minimum required version."""
        try:
            return pkg_version.parse(version) >= pkg_version.parse(min_version)
        except Exception:
            return False


# Register v1.0.0 schema
SchemaRegistry.register(IRSchemaVersion.V1_0_0.value, SymbolicScoreIR)

# Register v2.0.0 schema
SchemaRegistry.register(IRSchemaVersion.V2_0_0.value, SymbolicScoreIRV2)


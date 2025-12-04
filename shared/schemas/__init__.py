"""
Pydantic schemas for API requests and responses.
"""

from shared.schemas.base import BaseSchema, ErrorResponse, SuccessResponse
from shared.schemas.config import ConfigSchema
from shared.schemas.memory import (
    ConsolidationJobSchema,
    ExtractionJobSchema,
    MemoryCreate,
    MemoryRevisionSchema,
    MemorySchema,
    MemoryUpdate,
    ProceduralMemoryCreate,
    ProceduralMemoryExecutionSchema,
    ProceduralMemorySchema,
    ProceduralMemoryUpdate,
)
from shared.schemas.session import (
    EventCreate,
    EventSchema,
    SessionCreate,
    SessionSchema,
    SessionUpdate,
)

__all__ = [
    # Base
    "BaseSchema",
    "SuccessResponse",
    "ErrorResponse",
    # Session schemas
    "SessionSchema",
    "SessionCreate",
    "SessionUpdate",
    "EventSchema",
    "EventCreate",
    # Memory schemas
    "MemorySchema",
    "MemoryCreate",
    "MemoryUpdate",
    "MemoryRevisionSchema",
    "ProceduralMemorySchema",
    "ProceduralMemoryCreate",
    "ProceduralMemoryUpdate",
    "ProceduralMemoryExecutionSchema",
    "ExtractionJobSchema",
    "ConsolidationJobSchema",
    # Config
    "ConfigSchema",
]

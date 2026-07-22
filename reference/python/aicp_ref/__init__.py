"""AICP Core v0.1 reference helpers (minimal correctness-first)."""
from .session_state import (
    PROJECTION_OBJECT_TYPE,
    PROJECTION_VERSION,
    is_strict_session_state_projection,
    project_session_state,
    validate_session_state_projection,
)

__all__ = [
    "PROJECTION_OBJECT_TYPE",
    "PROJECTION_VERSION",
    "is_strict_session_state_projection",
    "project_session_state",
    "validate_session_state_projection",
]

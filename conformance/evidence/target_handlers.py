from __future__ import annotations

from typing import Any

from projection_v1_handler import ProjectionV1Handler


HANDLERS: dict[str, Any] = {
    ProjectionV1Handler.handler_id: ProjectionV1Handler(),
}


def resolve_handler(handler_id: str) -> Any:
    handler = HANDLERS.get(handler_id)
    if handler is None:
        raise ValueError("target registered but handler unavailable")
    return handler

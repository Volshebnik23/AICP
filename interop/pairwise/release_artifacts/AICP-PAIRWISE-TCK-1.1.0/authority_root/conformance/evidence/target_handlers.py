from __future__ import annotations

from typing import Any

from projection_v1_handler import ProjectionV1Handler
from product_profile_handler import ProductProfileV01Handler
from live_bindings.live_binding_handler import LiveBindingV01Handler


HANDLERS: dict[str, Any] = {
    ProjectionV1Handler.handler_id: ProjectionV1Handler(),
    ProductProfileV01Handler.handler_id: ProductProfileV01Handler(),
    LiveBindingV01Handler.handler_id: LiveBindingV01Handler(),
}


def resolve_handler(handler_id: str) -> Any:
    handler = HANDLERS.get(handler_id)
    if handler is None:
        raise ValueError("target registered but handler unavailable")
    return handler

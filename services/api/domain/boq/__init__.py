"""BOQ and evidence domain exports (lazy-loaded to avoid circular imports)."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["BOQService", "BOQSpecificationService"]

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    "BOQService": ("services.api.domain.boq.service", "BOQService"),
    "BOQSpecificationService": ("services.api.domain.boq.specification_service", "BOQSpecificationService"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORT_MAP.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value

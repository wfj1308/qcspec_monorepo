"""Photos domain exports (lazy-loaded to avoid circular imports)."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["PhotosService"]


def __getattr__(name: str) -> Any:
    if name != "PhotosService":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module("services.api.domain.photos.service")
    value = getattr(module, name)
    globals()[name] = value
    return value

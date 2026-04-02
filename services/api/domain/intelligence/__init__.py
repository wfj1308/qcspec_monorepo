"""Analytics and intelligence domain exports (lazy-loaded to avoid circular imports)."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["IntelligenceService"]


def __getattr__(name: str) -> Any:
    if name != "IntelligenceService":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module("services.api.domain.intelligence.service")
    value = getattr(module, name)
    globals()[name] = value
    return value

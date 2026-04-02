"""Public verify domain exports (lazy-loaded to avoid circular imports)."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["PublicVerifyService"]


def __getattr__(name: str) -> Any:
    if name != "PublicVerifyService":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module("services.api.domain.verify.service")
    value = getattr(module, name)
    globals()[name] = value
    return value

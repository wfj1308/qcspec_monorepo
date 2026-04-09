"""SignPeg domain exports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["SignPegService"]


def __getattr__(name: str) -> Any:
    if name != "SignPegService":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module("services.api.domain.signpeg.service")
    value = getattr(module, name)
    globals()[name] = value
    return value


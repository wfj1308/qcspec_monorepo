"""BOQPeg product exports (independent product facade)."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "BOQPegService",
    "boqpeg_phase1_bridge_pile_report",
    "boqpeg_product_manifest",
]

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    "BOQPegService": ("services.api.domain.boqpeg", "BOQPegService"),
    "boqpeg_product_manifest": ("services.api.domain.boqpeg", "boqpeg_product_manifest"),
    "boqpeg_phase1_bridge_pile_report": ("services.api.domain.boqpeg", "boqpeg_phase1_bridge_pile_report"),
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


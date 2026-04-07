"""NormRef product exports (compatibility facade)."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "BOQSpecificationService",
    "get_specir_object",
    "list_spu_library",
    "resolve_spu_ref_pack",
    "seed_specir_baseline",
    "validate_spu_content",
]

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    "BOQSpecificationService": ("services.api.domain.boq", "BOQSpecificationService"),
    "get_specir_object": ("services.api.domain.specir", "get_specir_object"),
    "list_spu_library": ("services.api.domain.specir", "list_spu_library"),
    "resolve_spu_ref_pack": ("services.api.domain.specir", "resolve_spu_ref_pack"),
    "seed_specir_baseline": ("services.api.domain.specir", "seed_specir_baseline"),
    "validate_spu_content": ("services.api.domain.specir", "validate_spu_content"),
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


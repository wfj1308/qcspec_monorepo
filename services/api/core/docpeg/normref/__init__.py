"""DocPeg NormRef kernel exports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["NormRefResolverPort", "NormRefResolverService"]

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    "NormRefResolverPort": ("services.api.core.docpeg.normref.ports", "NormRefResolverPort"),
    "NormRefResolverService": ("services.api.core.docpeg.normref.service", "NormRefResolverService"),
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

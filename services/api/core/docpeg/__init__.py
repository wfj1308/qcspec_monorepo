"""DocPeg kernel namespace.

This package provides a forward-compatible import surface for kernel modules.
Current implementations are shimmed to existing core services and will be
incrementally decoupled from domain implementations in later refactor steps.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "NormRefResolverService",
    "ProofUTXOService",
    "ProofKernelRecord",
    "TripExecutionEnvelope",
    "AuditEvent",
    "DocPegExecutionGateService",
    "DTORole",
    "Role",
    "BaseDTO",
]

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    "NormRefResolverService": ("services.api.core.docpeg.normref", "NormRefResolverService"),
    "ProofUTXOService": ("services.api.core.docpeg.utxo", "ProofUTXOService"),
    "ProofKernelRecord": ("services.api.core.docpeg.proof", "ProofKernelRecord"),
    "TripExecutionEnvelope": ("services.api.core.docpeg.trip", "TripExecutionEnvelope"),
    "AuditEvent": ("services.api.core.docpeg.audit", "AuditEvent"),
    "DocPegExecutionGateService": ("services.api.core.docpeg.access", "DocPegExecutionGateService"),
    "DTORole": ("services.api.core.docpeg.view", "DTORole"),
    "Role": ("services.api.core.docpeg.view", "Role"),
    "BaseDTO": ("services.api.core.docpeg.view", "BaseDTO"),
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

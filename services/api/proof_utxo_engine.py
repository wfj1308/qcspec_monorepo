"""Compatibility shim for the UTXO engine implementation.

Prefer importing :class:`ProofUTXOEngine` from
``services.api.domain.utxo.integrations``.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["ProofUTXOEngine"]


def __getattr__(name: str) -> Any:
    if name == "ProofUTXOEngine":
        module = import_module("services.api.domain.utxo.integrations")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""Backward-compatible export shim for ``ProofUTXOEngine``.

Prefer importing from ``services.api.domain.utxo.integrations``.
"""

from services.api.domain.utxo.integrations import ProofUTXOEngine

__all__ = ["ProofUTXOEngine"]

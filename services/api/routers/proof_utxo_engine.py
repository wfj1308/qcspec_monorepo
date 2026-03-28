"""
Backward-compatible export shim for ProofUTXOEngine.
Prefer importing from services.api.proof_utxo_engine.
"""

from services.api.proof_utxo_engine import ProofUTXOEngine

__all__ = ["ProofUTXOEngine"]

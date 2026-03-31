"""UTXO service façade exported from the sovereignty core layer."""

from __future__ import annotations

from supabase import Client

from services.api.core.base import BaseService
from services.api.proof_utxo_engine import ProofUTXOEngine


class ProofUTXOService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)
        self.engine = ProofUTXOEngine(sb)

    def create(self, **kwargs):
        return self.engine.create(**kwargs)

    def consume(self, **kwargs):
        return self.engine.consume(**kwargs)

    def get_unspent(self, **kwargs):
        return self.engine.get_unspent(**kwargs)

    def get_by_id(self, proof_id: str):
        return self.engine.get_by_id(proof_id)

    def get_chain(self, proof_id: str, max_depth: int = 128):
        return self.engine.get_chain(proof_id, max_depth=max_depth)

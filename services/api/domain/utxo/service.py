"""UTXO application facade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.utxo.helpers import (
    auto_settle_from_inspection_flow,
    consume_utxo_flow,
    create_utxo_flow,
    get_utxo_chain_flow,
    get_utxo_flow,
    list_unspent_utxo_flow,
    list_utxo_transactions_flow,
)


class UTXOService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def list_unspent(
        self,
        *,
        project_uri: str,
        proof_type: str | None,
        result: str | None,
        segment_uri: str | None,
        limit: int,
    ) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "list_unspent_utxo",
            list_unspent_utxo_flow,
            project_uri=project_uri,
            proof_type=proof_type,
            result=result,
            segment_uri=segment_uri,
            limit=limit,
            sb=supabase,
        )

    async def create(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("create_utxo", create_utxo_flow, body=body, sb=supabase)

    async def consume(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("consume_utxo", consume_utxo_flow, body=body, sb=supabase)

    async def auto_settle_from_inspection(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "auto_settle_from_inspection",
            auto_settle_from_inspection_flow,
            body=body,
            sb=supabase,
        )

    async def get_utxo(self, *, proof_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_utxo", get_utxo_flow, proof_id=proof_id, sb=supabase)

    async def get_chain(self, *, proof_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_utxo_chain", get_utxo_chain_flow, proof_id=proof_id, sb=supabase)

    async def list_transactions(self, *, project_uri: str | None, limit: int) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "list_utxo_transactions",
            list_utxo_transactions_flow,
            project_uri=project_uri,
            limit=limit,
            sb=supabase,
        )

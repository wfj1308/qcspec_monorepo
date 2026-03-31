"""UTXO application facade."""

from __future__ import annotations

from typing import Any
import uuid

from fastapi import HTTPException
from supabase import Client

from services.api.core.base import BaseService
from services.api.proof_utxo_engine import ProofUTXOEngine


class UTXOService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    def _engine(self) -> ProofUTXOEngine:
        return ProofUTXOEngine(self.require_supabase())

    async def list_unspent(
        self,
        *,
        project_uri: str,
        proof_type: str | None,
        result: str | None,
        segment_uri: str | None,
        limit: int,
    ) -> Any:
        return await self.run_guarded(
            "list_unspent_utxo",
            self._list_unspent,
            project_uri=project_uri,
            proof_type=proof_type,
            result=result,
            segment_uri=segment_uri,
            limit=limit,
        )

    async def create(self, *, body: Any) -> Any:
        return await self.run_guarded("create_utxo", self._create, body=body)

    async def consume(self, *, body: Any) -> Any:
        return await self.run_guarded("consume_utxo", self._consume, body=body)

    async def auto_settle_from_inspection(self, *, body: Any) -> Any:
        return await self.run_guarded(
            "auto_settle_from_inspection",
            self._auto_settle_from_inspection,
            body=body,
        )

    async def get_utxo(self, *, proof_id: str) -> Any:
        return await self.run_guarded("get_utxo", self._get_utxo, proof_id=proof_id)

    async def get_chain(self, *, proof_id: str) -> Any:
        return await self.run_guarded("get_utxo_chain", self._get_chain, proof_id=proof_id)

    async def list_transactions(self, *, project_uri: str | None, limit: int) -> Any:
        return await self.run_guarded(
            "list_utxo_transactions",
            self._list_transactions,
            project_uri=project_uri,
            limit=limit,
        )

    def _list_unspent(
        self,
        *,
        project_uri: str,
        proof_type: str | None,
        result: str | None,
        segment_uri: str | None,
        limit: int,
    ) -> dict[str, Any]:
        rows = self._engine().get_unspent(
            project_uri=project_uri,
            proof_type=proof_type,
            result=result,
            segment_uri=segment_uri,
            limit=limit,
        )
        return {"data": rows, "count": len(rows)}

    def _create(self, *, body: Any) -> dict[str, Any]:
        proof_id = str(body.proof_id or f"GP-PROOF-{uuid.uuid4().hex[:16].upper()}")
        return self._engine().create(
            proof_id=proof_id,
            owner_uri=body.owner_uri,
            project_id=body.project_id,
            project_uri=body.project_uri,
            segment_uri=body.segment_uri,
            proof_type=body.proof_type,
            result=body.result,
            state_data=body.state_data or {},
            conditions=body.conditions or [],
            parent_proof_id=body.parent_proof_id,
            norm_uri=body.norm_uri,
            signer_uri=body.signer_uri,
            signer_role=body.signer_role,
            gitpeg_anchor=body.gitpeg_anchor,
        )

    def _consume(self, *, body: Any) -> dict[str, Any]:
        return self._engine().consume(
            input_proof_ids=[str(x) for x in (body.input_proof_ids or [])],
            output_states=list(body.output_states or []),
            executor_uri=body.executor_uri,
            executor_role=body.executor_role,
            trigger_action=body.trigger_action,
            trigger_data=body.trigger_data or {},
            tx_type=body.tx_type,
        )

    def _auto_settle_from_inspection(self, *, body: Any) -> dict[str, Any]:
        return self._engine().auto_consume_inspection_pass(
            inspection_proof_id=body.inspection_proof_id,
            executor_uri=body.executor_uri,
            executor_role=body.executor_role,
            trigger_action=body.trigger_action,
            anchor_config=body.anchor_config or {},
        )

    def _get_utxo(self, *, proof_id: str) -> dict[str, Any]:
        row = self._engine().get_by_id(proof_id)
        if not row:
            raise HTTPException(404, "proof_utxo not found")
        return row

    def _get_chain(self, *, proof_id: str) -> dict[str, Any]:
        chain = self._engine().get_chain(proof_id)
        if not chain:
            raise HTTPException(404, "proof chain not found")
        return {"proof_id": proof_id, "depth": len(chain), "chain": chain}

    def _list_transactions(self, *, project_uri: str | None, limit: int) -> dict[str, Any]:
        rows = (
            self.require_supabase()
            .table("proof_transaction")
            .select("*")
            .order("created_at", desc=True)
            .limit(max(1, min(limit, 500)))
            .execute()
            .data
            or []
        )
        if project_uri:
            engine = self._engine()
            filtered: list[dict[str, Any]] = []
            for tx in rows:
                outputs = tx.get("output_proofs") or []
                if any((engine.get_by_id(str(pid)) or {}).get("project_uri") == project_uri for pid in outputs):
                    filtered.append(tx)
            rows = filtered
        return {"data": rows, "count": len(rows)}

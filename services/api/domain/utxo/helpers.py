"""UTXO flow helpers used by routers and domain services."""

from __future__ import annotations

from typing import Any
import uuid

from fastapi import HTTPException
from supabase import Client

from services.api.domain.utxo.integrations import ProofUTXOEngine


def list_unspent_utxo_flow(
    *,
    project_uri: str,
    proof_type: str | None,
    result: str | None,
    segment_uri: str | None,
    limit: int,
    sb: Client,
) -> dict[str, Any]:
    rows = ProofUTXOEngine(sb).get_unspent(
        project_uri=project_uri,
        proof_type=proof_type,
        result=result,
        segment_uri=segment_uri,
        limit=limit,
    )
    return {"data": rows, "count": len(rows)}


def create_utxo_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    proof_id = str(body.proof_id or f"GP-PROOF-{uuid.uuid4().hex[:16].upper()}")
    return ProofUTXOEngine(sb).create(
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


def consume_utxo_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return ProofUTXOEngine(sb).consume(
        input_proof_ids=[str(x) for x in (body.input_proof_ids or [])],
        output_states=list(body.output_states or []),
        executor_uri=body.executor_uri,
        executor_role=body.executor_role,
        trigger_action=body.trigger_action,
        trigger_data=body.trigger_data or {},
        tx_type=body.tx_type,
    )


def auto_settle_from_inspection_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return ProofUTXOEngine(sb).auto_consume_inspection_pass(
        inspection_proof_id=body.inspection_proof_id,
        executor_uri=body.executor_uri,
        executor_role=body.executor_role,
        trigger_action=body.trigger_action,
        anchor_config=body.anchor_config or {},
    )


def get_utxo_flow(*, proof_id: str, sb: Client) -> dict[str, Any]:
    row = ProofUTXOEngine(sb).get_by_id(proof_id)
    if not row:
        raise HTTPException(404, "proof_utxo not found")
    return row


def get_utxo_chain_flow(*, proof_id: str, sb: Client) -> dict[str, Any]:
    chain = ProofUTXOEngine(sb).get_chain(proof_id)
    if not chain:
        raise HTTPException(404, "proof chain not found")
    return {"proof_id": proof_id, "depth": len(chain), "chain": chain}


def list_utxo_transactions_flow(
    *,
    project_uri: str | None,
    limit: int,
    sb: Client,
) -> dict[str, Any]:
    q = (
        sb.table("proof_transaction")
        .select("*")
        .order("created_at", desc=True)
        .limit(max(1, min(limit, 500)))
    )
    rows = q.execute().data or []
    if project_uri:
        filtered: list[dict[str, Any]] = []
        engine = ProofUTXOEngine(sb)
        for tx in rows:
            outputs = tx.get("output_proofs") or []
            matched = False
            for pid in outputs:
                row = engine.get_by_id(str(pid))
                if row and row.get("project_uri") == project_uri:
                    matched = True
                    break
            if matched:
                filtered.append(tx)
        rows = filtered
    return {"data": rows, "count": len(rows)}

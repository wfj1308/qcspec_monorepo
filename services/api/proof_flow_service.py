"""
Flow helpers for proof router.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID
import uuid

import httpx
from fastapi import HTTPException
from postgrest.exceptions import APIError
from supabase import Client

from services.api.proof_utxo_engine import ProofUTXOEngine


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except Exception:
        return False


def _run_with_retry(fn: Any, retries: int = 1):
    last_err = None
    for _ in range(retries + 1):
        try:
            return fn()
        except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout) as e:
            last_err = e
            continue
    if last_err:
        raise last_err


def _utxo_to_legacy_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "proof_id": row.get("proof_id"),
        "proof_hash": row.get("proof_hash"),
        "v_uri": (row.get("state_data") or {}).get("v_uri") or row.get("project_uri"),
        "object_type": row.get("proof_type"),
        "action": "consume" if row.get("spent") else "create",
        "summary": f"{row.get('proof_type')}:{row.get('result')}",
        "created_at": row.get("created_at"),
    }


def _anchor_status(anchor: str) -> str:
    value = str(anchor or "").strip()
    if not value:
        return "pending"
    if value.lower() in {"pending", "pending_anchor", "to_anchor"}:
        return "pending"
    return "anchored"


async def list_proofs_flow(
    *,
    project_id: str,
    v_uri: str | None,
    limit: int,
    sb: Client,
) -> dict[str, Any]:
    if not _is_uuid(project_id):
        raise HTTPException(400, "Invalid project_id format. UUID expected.")

    def _query():
        q = (
            sb.table("proof_chain")
            .select("proof_id,proof_hash,v_uri,object_type,action,summary,created_at")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .limit(max(1, min(limit, 200)))
        )
        if v_uri:
            q = q.eq("v_uri", v_uri)
        return q.execute()

    try:
        res = _run_with_retry(_query, retries=1)
        rows = res.data or []
        return {"data": rows, "count": len(rows)}
    except APIError as e:
        if "invalid input syntax for type uuid" in str(e):
            raise HTTPException(400, "Invalid project_id format. UUID expected.")
        try:
            proj = (
                sb.table("projects")
                .select("v_uri")
                .eq("id", project_id)
                .limit(1)
                .execute()
            )
            rows: list[dict[str, Any]] = []
            if proj.data:
                engine = ProofUTXOEngine(sb)
                rows = [_utxo_to_legacy_row(x) for x in engine.get_unspent(project_uri=proj.data[0]["v_uri"], limit=limit)]
            return {"data": rows, "count": len(rows)}
        except Exception:
            raise HTTPException(502, "Failed to query proof chain.")
    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        return {"data": [], "count": 0}


async def verify_proof_flow(*, proof_id: str, sb: Client) -> dict[str, Any]:
    try:
        res = _run_with_retry(
            lambda: sb.table("proof_chain").select("*").eq("proof_id", proof_id).single().execute(),
            retries=1,
        )
    except (APIError, httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        res = None

    if not res or not res.data:
        try:
            utxo = ProofUTXOEngine(sb).get_by_id(proof_id)
        except Exception:
            utxo = None

        if not utxo:
            return {"valid": False, "proof": None, "message": "Proof not found."}

        anchor = str(utxo.get("gitpeg_anchor") or "").strip()
        return {
            "valid": True,
            "proof_id": proof_id,
            "proof_hash": utxo.get("proof_hash"),
            "v_uri": (utxo.get("state_data") or {}).get("v_uri") or utxo.get("project_uri"),
            "project_uri": utxo.get("project_uri"),
            "segment_uri": utxo.get("segment_uri"),
            "object_type": utxo.get("proof_type"),
            "action": "consume" if utxo.get("spent") else "create",
            "summary": f"{utxo.get('proof_type')}:{utxo.get('result')}",
            "created_at": utxo.get("created_at"),
            "chain_length": int(utxo.get("depth") or 0) + 1,
            "gitpeg_anchor": anchor or None,
            "anchor_status": _anchor_status(anchor),
            "message": "Proof verified via proof_utxo.",
        }

    proof = res.data
    expected_hash = str(proof_id).replace("GP-PROOF-", "").lower()
    hash_valid = proof.get("proof_hash") == expected_hash

    try:
        chain_len = _run_with_retry(
            lambda: sb.table("proof_chain").select("proof_id", count="exact").eq("v_uri", proof.get("v_uri")).execute(),
            retries=1,
        )
        chain_count = chain_len.count or 0
    except Exception:
        chain_count = 0

    utxo_extra: dict[str, Any] = {}
    try:
        utxo = ProofUTXOEngine(sb).get_by_id(proof_id)
    except Exception:
        utxo = None

    if isinstance(utxo, dict):
        anchor = str(utxo.get("gitpeg_anchor") or "").strip()
        utxo_extra = {
            "project_uri": utxo.get("project_uri"),
            "segment_uri": utxo.get("segment_uri"),
            "proof_hash": utxo.get("proof_hash"),
            "gitpeg_anchor": anchor or None,
            "anchor_status": _anchor_status(anchor),
        }

    return {
        "valid": hash_valid,
        "proof_id": proof_id,
        "proof_hash": proof.get("proof_hash"),
        "v_uri": proof.get("v_uri"),
        "object_type": proof.get("object_type"),
        "action": proof.get("action"),
        "summary": proof.get("summary"),
        "created_at": proof.get("created_at"),
        "chain_length": chain_count,
        "message": "Proof verified." if hash_valid else "Proof hash mismatch.",
        **utxo_extra,
    }


async def get_node_tree_flow(*, root_uri: str, sb: Client) -> dict[str, Any]:
    try:
        res = _run_with_retry(
            lambda: sb.table("v_nodes")
            .select("uri,parent_uri,node_type,peg_count,status")
            .like("uri", f"{root_uri}%")
            .order("uri")
            .execute(),
            retries=1,
        )
        return {"data": res.data or [], "root": root_uri}
    except Exception:
        return {"data": [], "root": root_uri}


async def proof_stats_flow(*, project_id: str, sb: Client) -> dict[str, Any]:
    if not _is_uuid(project_id):
        raise HTTPException(400, "Invalid project_id format. UUID expected.")

    try:
        res = _run_with_retry(
            lambda: sb.table("proof_chain").select("object_type, action").eq("project_id", project_id).execute(),
            retries=1,
        )
        rows = res.data or []
    except Exception:
        rows = []

    by_type: dict[str, int] = {}
    by_action: dict[str, int] = {}
    for row in rows:
        object_type = row.get("object_type")
        action = row.get("action")
        if object_type:
            by_type[object_type] = by_type.get(object_type, 0) + 1
        if action:
            by_action[action] = by_action.get(action, 0) + 1

    return {
        "total": len(rows),
        "by_type": by_type,
        "by_action": by_action,
    }


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

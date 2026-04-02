"""Proof query flow helpers used by compatibility layers."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.domain.proof.service import ProofApplicationService


async def list_proofs_flow(
    *,
    project_id: str,
    v_uri: str | None,
    limit: int,
    sb: Client,
) -> dict[str, Any]:
    return await ProofApplicationService(sb=sb).list_proofs(project_id=project_id, v_uri=v_uri, limit=limit)


async def verify_proof_flow(*, proof_id: str, sb: Client) -> dict[str, Any]:
    return await ProofApplicationService(sb=sb).verify_proof(proof_id=proof_id)


async def get_node_tree_flow(*, root_uri: str, sb: Client) -> dict[str, Any]:
    return await ProofApplicationService(sb=sb).get_node_tree(root_uri=root_uri)


async def proof_stats_flow(*, project_id: str, sb: Client) -> dict[str, Any]:
    return await ProofApplicationService(sb=sb).proof_stats(project_id=project_id)

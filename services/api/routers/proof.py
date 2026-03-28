"""QCSpec proof routes.
services/api/routers/proof.py
"""

from typing import Optional

from fastapi import APIRouter, Depends
from supabase import Client

from services.api.dependencies import get_supabase
from services.api.proof_flow_service import (
    auto_settle_from_inspection_flow,
    consume_utxo_flow,
    create_utxo_flow,
    get_node_tree_flow,
    get_utxo_chain_flow,
    get_utxo_flow,
    list_proofs_flow,
    list_unspent_utxo_flow,
    list_utxo_transactions_flow,
    proof_stats_flow,
    verify_proof_flow,
)
from services.api.proof_schemas import UTXOAutoSettleBody, UTXOConsumeBody, UTXOCreateBody

router = APIRouter()


@router.get("/")
async def list_proofs(
    project_id: str,
    v_uri: Optional[str] = None,
    limit: int = 50,
    sb: Client = Depends(get_supabase),
):
    return await list_proofs_flow(project_id=project_id, v_uri=v_uri, limit=limit, sb=sb)


@router.get("/verify/{proof_id}")
async def verify_proof(
    proof_id: str,
    sb: Client = Depends(get_supabase),
):
    return await verify_proof_flow(proof_id=proof_id, sb=sb)


@router.get("/node-tree")
async def get_node_tree(
    root_uri: str,
    sb: Client = Depends(get_supabase),
):
    return await get_node_tree_flow(root_uri=root_uri, sb=sb)


@router.get("/stats/{project_id}")
async def proof_stats(
    project_id: str,
    sb: Client = Depends(get_supabase),
):
    return await proof_stats_flow(project_id=project_id, sb=sb)


@router.get("/utxo/unspent")
async def list_unspent_utxo(
    project_uri: str,
    proof_type: Optional[str] = None,
    result: Optional[str] = None,
    segment_uri: Optional[str] = None,
    limit: int = 200,
    sb: Client = Depends(get_supabase),
):
    return list_unspent_utxo_flow(
        project_uri=project_uri,
        proof_type=proof_type,
        result=result,
        segment_uri=segment_uri,
        limit=limit,
        sb=sb,
    )


@router.post("/utxo/create")
async def create_utxo(body: UTXOCreateBody, sb: Client = Depends(get_supabase)):
    return create_utxo_flow(body=body, sb=sb)


@router.post("/utxo/consume")
async def consume_utxo(body: UTXOConsumeBody, sb: Client = Depends(get_supabase)):
    return consume_utxo_flow(body=body, sb=sb)


@router.post("/utxo/auto/inspection-settle")
async def auto_settle_from_inspection(body: UTXOAutoSettleBody, sb: Client = Depends(get_supabase)):
    return auto_settle_from_inspection_flow(body=body, sb=sb)


@router.get("/utxo/{proof_id}")
async def get_utxo(proof_id: str, sb: Client = Depends(get_supabase)):
    return get_utxo_flow(proof_id=proof_id, sb=sb)


@router.get("/utxo/{proof_id}/chain")
async def get_utxo_chain(proof_id: str, sb: Client = Depends(get_supabase)):
    return get_utxo_chain_flow(proof_id=proof_id, sb=sb)


@router.get("/utxo/transactions/list")
async def list_utxo_transactions(
    project_uri: Optional[str] = None,
    limit: int = 100,
    sb: Client = Depends(get_supabase),
):
    return list_utxo_transactions_flow(project_uri=project_uri, limit=limit, sb=sb)

"""UTXO ledger routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from services.api.dependencies import get_utxo_application_service
from services.api.domain import UTXOService
from services.api.domain.proof.schemas import UTXOAutoSettleBody, UTXOConsumeBody, UTXOCreateBody

router = APIRouter()


@router.get("/utxo/unspent")
async def list_unspent_utxo(
    project_uri: str,
    proof_type: Optional[str] = None,
    result: Optional[str] = None,
    segment_uri: Optional[str] = None,
    limit: int = 200,
    utxo_service: UTXOService = Depends(get_utxo_application_service),
):
    return await utxo_service.list_unspent(
        project_uri=project_uri,
        proof_type=proof_type,
        result=result,
        segment_uri=segment_uri,
        limit=limit,
    )


@router.post("/utxo/create")
async def create_utxo(
    body: UTXOCreateBody,
    utxo_service: UTXOService = Depends(get_utxo_application_service),
):
    return await utxo_service.create(body=body)


@router.post("/utxo/consume")
async def consume_utxo(
    body: UTXOConsumeBody,
    utxo_service: UTXOService = Depends(get_utxo_application_service),
):
    return await utxo_service.consume(body=body)


@router.post("/utxo/auto/inspection-settle")
async def auto_settle_from_inspection(
    body: UTXOAutoSettleBody,
    utxo_service: UTXOService = Depends(get_utxo_application_service),
):
    return await utxo_service.auto_settle_from_inspection(body=body)


@router.get("/utxo/{proof_id}")
async def get_utxo(
    proof_id: str,
    utxo_service: UTXOService = Depends(get_utxo_application_service),
):
    return await utxo_service.get_utxo(proof_id=proof_id)


@router.get("/utxo/{proof_id}/chain")
async def get_utxo_chain(
    proof_id: str,
    utxo_service: UTXOService = Depends(get_utxo_application_service),
):
    return await utxo_service.get_chain(proof_id=proof_id)


@router.get("/utxo/transactions/list")
async def list_utxo_transactions(
    project_uri: Optional[str] = None,
    limit: int = 100,
    utxo_service: UTXOService = Depends(get_utxo_application_service),
):
    return await utxo_service.list_transactions(project_uri=project_uri, limit=limit)

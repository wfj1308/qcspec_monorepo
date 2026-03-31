"""QCSpec proof routes.
services/api/routers/proof.py
"""

from typing import Optional

from fastapi import APIRouter, Depends

from services.api.dependencies import get_proof_application_service
from services.api.domain import ProofApplicationService

router = APIRouter()
public_router = APIRouter()


@router.get("/")
async def list_proofs(
    project_id: str,
    v_uri: Optional[str] = None,
    limit: int = 50,
    proof_service: ProofApplicationService = Depends(get_proof_application_service),
):
    return await proof_service.list_proofs(project_id=project_id, v_uri=v_uri, limit=limit)


@router.get("/verify/{proof_id}")
async def verify_proof(
    proof_id: str,
    proof_service: ProofApplicationService = Depends(get_proof_application_service),
):
    return await proof_service.verify_proof(proof_id=proof_id)


@router.get("/node-tree")
async def get_node_tree(
    root_uri: str,
    proof_service: ProofApplicationService = Depends(get_proof_application_service),
):
    return await proof_service.get_node_tree(root_uri=root_uri)


@router.get("/stats/{project_id}")
async def proof_stats(
    project_id: str,
    proof_service: ProofApplicationService = Depends(get_proof_application_service),
):
    return await proof_service.proof_stats(project_id=project_id)

"""Document governance routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from services.api.dependencies import get_document_governance_service
from services.api.domain import DocumentGovernanceService
from services.api.domain.proof.schemas import DocAutoClassifyBody, DocNodeAutoGenerateBody, DocNodeCreateBody, DocSearchBody

router = APIRouter()


@router.post("/docs/auto-classify")
async def auto_classify_doc(
    body: DocAutoClassifyBody,
    documents_service: DocumentGovernanceService = Depends(get_document_governance_service),
):
    return await documents_service.auto_classify(body=body)


@router.get("/docs/tree")
async def get_doc_tree(
    project_uri: str,
    root_uri: str = "",
    documents_service: DocumentGovernanceService = Depends(get_document_governance_service),
):
    return await documents_service.tree(project_uri=project_uri, root_uri=root_uri)


@router.post("/docs/node/create")
async def create_doc_node(
    body: DocNodeCreateBody,
    documents_service: DocumentGovernanceService = Depends(get_document_governance_service),
):
    return await documents_service.create_node(body=body)


@router.post("/docs/node/auto-generate")
async def auto_generate_doc_nodes(
    body: DocNodeAutoGenerateBody,
    documents_service: DocumentGovernanceService = Depends(get_document_governance_service),
):
    return await documents_service.auto_generate_nodes(body=body)


@router.post("/docs/search")
async def search_docs(
    body: DocSearchBody,
    documents_service: DocumentGovernanceService = Depends(get_document_governance_service),
):
    return await documents_service.search(body=body)


@router.post("/docs/register")
async def register_doc_upload(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    node_uri: str = Form(""),
    source_utxo_id: str = Form(...),
    executor_uri: str = Form("v://executor/system/"),
    text_excerpt: str = Form(""),
    tags: str = Form(""),
    custom_metadata: str = Form(""),
    ai_metadata: str = Form(""),
    doc_spec: str = Form(""),
    dtorole_context: str = Form(""),
    auto_classify: bool = Form(True),
    documents_service: DocumentGovernanceService = Depends(get_document_governance_service),
):
    return await documents_service.register_upload(
        file=file,
        project_uri=project_uri,
        node_uri=node_uri,
        source_utxo_id=source_utxo_id,
        executor_uri=executor_uri,
        text_excerpt=text_excerpt,
        tags=tags,
        custom_metadata=custom_metadata,
        ai_metadata=ai_metadata,
        doc_spec=doc_spec,
        dtorole_context=dtorole_context,
        auto_classify=auto_classify,
    )

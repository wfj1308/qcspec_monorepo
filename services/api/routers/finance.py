"""Finance and settlement routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from services.api.dependencies import get_finance_audit_service, get_proof_application_service
from services.api.domain import FinanceAuditService, ProofApplicationService
from services.api.domain.proof.schemas import DocFinalExportBody, DocFinalFinalizeBody, PaymentCertificateBody, RailPactInstructionBody

router = APIRouter()


@router.get("/docfinal/context")
async def get_docfinal_context(
    boq_item_uri: str,
    project_name: Optional[str] = None,
    verify_base_url: str = "https://verify.qcspec.com",
    template_path: Optional[str] = None,
    aggregate_anchor_code: str = "",
    aggregate_direction: str = "all",
    aggregate_level: str = "all",
    proof_service: ProofApplicationService = Depends(get_proof_application_service),
):
    return await proof_service.get_docfinal_context(
        boq_item_uri=boq_item_uri,
        project_name=project_name,
        verify_base_url=verify_base_url,
        template_path=template_path,
        aggregate_anchor_code=aggregate_anchor_code,
        aggregate_direction=aggregate_direction,
        aggregate_level=aggregate_level,
    )


@router.get("/docfinal/download")
async def download_docfinal(
    boq_item_uri: str,
    project_name: Optional[str] = None,
    verify_base_url: str = "https://verify.qcspec.com",
    template_path: Optional[str] = None,
    aggregate_anchor_code: str = "",
    aggregate_direction: str = "all",
    aggregate_level: str = "all",
    proof_service: ProofApplicationService = Depends(get_proof_application_service),
):
    return await proof_service.download_docfinal(
        boq_item_uri=boq_item_uri,
        project_name=project_name,
        verify_base_url=verify_base_url,
        template_path=template_path,
        aggregate_anchor_code=aggregate_anchor_code,
        aggregate_direction=aggregate_direction,
        aggregate_level=aggregate_level,
    )


@router.post("/docfinal/export")
async def export_doc_final(
    body: DocFinalExportBody,
    proof_service: ProofApplicationService = Depends(get_proof_application_service),
):
    return await proof_service.export_doc_final(body=body)


@router.post("/docfinal/finalize")
async def finalize_docfinal_delivery(
    body: DocFinalFinalizeBody,
    proof_service: ProofApplicationService = Depends(get_proof_application_service),
):
    return await proof_service.finalize_docfinal_delivery(body=body)


@router.post("/payment/certificate/generate")
async def generate_payment_certificate(
    body: PaymentCertificateBody,
    finance_service: FinanceAuditService = Depends(get_finance_audit_service),
):
    return await finance_service.payment_certificate(body=body)


@router.get("/payment/audit-trace/{payment_id}")
async def payment_audit_trace(
    payment_id: str,
    verify_base_url: str = "https://verify.qcspec.com",
    finance_service: FinanceAuditService = Depends(get_finance_audit_service),
):
    return await finance_service.audit_trace(payment_id=payment_id, verify_base_url=verify_base_url)


@router.post("/payment/railpact/instruction")
async def generate_railpact_instruction(
    body: RailPactInstructionBody,
    finance_service: FinanceAuditService = Depends(get_finance_audit_service),
):
    return await finance_service.railpact_instruction(body=body)

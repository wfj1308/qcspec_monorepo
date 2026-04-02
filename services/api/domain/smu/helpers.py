"""SMU flow helpers used by routers and domain services."""

from __future__ import annotations

from typing import Any

from fastapi import UploadFile
from supabase import Client

from services.api.core.http import read_upload_content_sync
from services.api.domain.smu.flows import (
    execute_smu_trip,
    freeze_smu,
    get_governance_context,
    import_genesis_trip,
    list_spu_template_library,
    preview_genesis_tree,
    retry_erpnext_push_queue as retry_erpnext_push_queue_smu,
    sign_smu_approval,
    validate_logic,
)

_SMU_UPLOAD_MAX_BYTES = 60 * 1024 * 1024


def _read_smu_upload_content(*, file: UploadFile) -> bytes:
    return read_upload_content_sync(
        file=file,
        max_bytes=_SMU_UPLOAD_MAX_BYTES,
        too_large_error="upload file too large, max 60MB",
    )


def smu_genesis_import_flow(
    *,
    file: UploadFile,
    project_uri: str,
    project_id: str,
    boq_root_uri: str,
    norm_context_root_uri: str,
    owner_uri: str,
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    content = _read_smu_upload_content(file=file)
    return import_genesis_trip(
        sb=sb,
        project_uri=project_uri,
        project_id=project_id,
        upload_file_name=str(file.filename or "boq.csv"),
        upload_content=content,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        commit=bool(commit),
    )


def smu_genesis_preview_flow(
    *,
    file: UploadFile,
    project_uri: str,
    project_id: str,
    boq_root_uri: str,
    norm_context_root_uri: str,
    owner_uri: str,
    sb: Client,
) -> dict[str, Any]:
    content = _read_smu_upload_content(file=file)
    return preview_genesis_tree(
        sb=sb,
        project_uri=project_uri,
        project_id=project_id,
        upload_file_name=str(file.filename or "boq.csv"),
        upload_content=content,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
    )


def smu_genesis_import_async_flow(
    *,
    file: UploadFile,
    project_uri: str,
    project_id: str,
    boq_root_uri: str,
    norm_context_root_uri: str,
    owner_uri: str,
    commit: bool,
) -> dict[str, Any]:
    content = _read_smu_upload_content(file=file)
    return start_smu_import_job(
        upload_file_name=str(file.filename or "boq.csv"),
        upload_content=content,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        commit=bool(commit),
    )


def smu_genesis_import_job_flow(*, job_id: str) -> dict[str, Any]:
    return get_smu_import_job(job_id)


def smu_genesis_import_active_job_flow(*, project_uri: str) -> dict[str, Any]:
    return get_active_smu_import_job(project_uri=project_uri)


def smu_spu_library_flow() -> dict[str, Any]:
    return list_spu_template_library()


def smu_node_context_flow(
    *,
    project_uri: str,
    boq_item_uri: str,
    component_type: str,
    measured_value: float | None,
    sb: Client,
) -> dict[str, Any]:
    return get_governance_context(
        sb=sb,
        project_uri=project_uri,
        boq_item_uri=boq_item_uri,
        component_type=component_type,
        measured_value=measured_value,
    )


def smu_execute_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return execute_smu_trip(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        input_proof_id=str(body.input_proof_id or ""),
        executor_uri=str(body.executor_uri or "v://executor/mobile/inspector/"),
        executor_did=str(body.executor_did or ""),
        executor_role=str(body.executor_role or "TRIPROLE"),
        component_type=str(body.component_type or "generic"),
        measurement=dict(body.measurement or {}),
        geo_location=dict(body.geo_location or {}),
        server_timestamp_proof=dict(body.server_timestamp_proof or {}),
        evidence_hashes=[str(x) for x in list(body.evidence_hashes or []) if str(x).strip()],
        credentials_vc=list(body.credentials_vc or []),
        force_reject=bool(getattr(body, "force_reject", False)),
    )


def smu_sign_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return sign_smu_approval(
        sb=sb,
        input_proof_id=str(body.input_proof_id or ""),
        boq_item_uri=str(body.boq_item_uri or ""),
        supervisor_executor_uri=str(body.supervisor_executor_uri or "v://executor/supervisor/mobile/"),
        supervisor_did=str(body.supervisor_did or ""),
        contractor_did=str(body.contractor_did or ""),
        owner_did=str(body.owner_did or ""),
        signer_metadata=dict(body.signer_metadata or {}),
        consensus_values=list(body.consensus_values or []),
        allowed_deviation=(float(body.allowed_deviation) if body.allowed_deviation is not None else None),
        allowed_deviation_percent=(
            float(body.allowed_deviation_percent) if body.allowed_deviation_percent is not None else None
        ),
        geo_location=dict(body.geo_location or {}),
        server_timestamp_proof=dict(body.server_timestamp_proof or {}),
        auto_docpeg=bool(body.auto_docpeg if body.auto_docpeg is not None else True),
        verify_base_url=str(body.verify_base_url or "https://verify.qcspec.com"),
        template_path=str(body.template_path or ""),
    )


def smu_validate_logic_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return validate_logic(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        smu_id=str(body.smu_id or ""),
    )


def smu_freeze_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return freeze_smu(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        smu_id=str(body.smu_id or ""),
        executor_uri=str(body.executor_uri or "v://executor/owner/system/"),
        min_risk_score=float(body.min_risk_score or 60.0),
    )


def retry_erpnext_push_queue(*, sb: Client, limit: int = 20) -> dict[str, Any]:
    return retry_erpnext_push_queue_smu(sb=sb, limit=limit)

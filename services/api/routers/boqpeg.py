"""BOQPeg upload and genesis routes."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile

from services.api.core.docpeg import DocPegExecutionGateService
from services.api.dependencies import (
    get_boqpeg_service,
    get_docpeg_execution_gate_service,
    require_auth_identity,
)
from services.api.domain import BOQPegService

router = APIRouter()
public_router = APIRouter()


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _resolve_body_project_uri(body: Any) -> str:
    payload = _as_dict(body)
    return _to_text(payload.get("project_uri")).strip()


def _resolve_body_node_uri(body: Any) -> str:
    payload = _as_dict(body)
    return _to_text(payload.get("node_uri") or payload.get("boq_item_uri") or payload.get("bridge_uri")).strip()


def _resolve_body_actor_uri(body: Any) -> str:
    payload = _as_dict(body)
    return _to_text(payload.get("actor_uri") or payload.get("owner_uri") or payload.get("executor_uri")).strip()


def _parse_json_object(raw: str, *, field_name: str) -> dict[str, Any]:
    text = _to_text(raw).strip()
    if not text:
        return {}
    try:
        decoded = json.loads(text)
    except Exception as exc:
        raise HTTPException(400, f"invalid {field_name}: {exc}") from exc
    if not isinstance(decoded, dict):
        raise HTTPException(400, f"{field_name} must decode to object")
    return decoded


def _resolve_identity_dto_role(identity: dict[str, Any]) -> str:
    if not isinstance(identity, dict):
        return ""
    direct = _to_text(identity.get("dto_role") or identity.get("role")).strip()
    if direct:
        return direct
    roles = identity.get("roles")
    if isinstance(roles, (list, tuple, set)):
        for role in roles:
            token = _to_text(role).strip()
            if token:
                return token
    return ""


def _enforce_docpeg_write(
    *,
    gate: DocPegExecutionGateService,
    identity: dict[str, Any],
    operation: str,
    project_uri: str = "",
    node_uri: str = "",
    actor_uri: str = "",
    body: Any = None,
) -> None:
    gate.enforce_execution(
        identity=identity,
        operation=operation,
        access_mode="write",
        project_uri=project_uri or _resolve_body_project_uri(body),
        node_uri=node_uri or _resolve_body_node_uri(body),
        actor_uri=actor_uri or _resolve_body_actor_uri(body),
    )


def _enforce_docpeg_read(
    *,
    gate: DocPegExecutionGateService,
    identity: dict[str, Any],
    operation: str,
    project_uri: str = "",
    node_uri: str = "",
    body: Any = None,
) -> None:
    gate.enforce_execution(
        identity=identity,
        operation=operation,
        access_mode="read",
        project_uri=project_uri or _resolve_body_project_uri(body),
        node_uri=node_uri or _resolve_body_node_uri(body),
    )


@router.post("/boqpeg/import")
async def import_boqpeg_upload(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    project_id: str = Form(""),
    boq_root_uri: str = Form(""),
    norm_context_root_uri: str = Form(""),
    owner_uri: str = Form(""),
    bridge_mappings_json: str = Form(""),
    commit: bool = Form(True),
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    bridge_mappings = _parse_json_object(bridge_mappings_json, field_name="bridge_mappings_json")
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_import_upload",
        project_uri=project_uri,
        actor_uri=owner_uri,
    )
    return await boqpeg_service.import_upload(
        file=file,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        bridge_mappings=bridge_mappings,
        dto_role=_resolve_identity_dto_role(identity),
        commit=commit,
    )


@router.get("/product/manifest")
async def get_boqpeg_product_manifest(
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    return await boqpeg_service.product_manifest()


@router.post("/boqpeg/preview")
async def preview_boqpeg_upload(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    project_id: str = Form(""),
    boq_root_uri: str = Form(""),
    norm_context_root_uri: str = Form(""),
    owner_uri: str = Form(""),
    bridge_mappings_json: str = Form(""),
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    bridge_mappings = _parse_json_object(bridge_mappings_json, field_name="bridge_mappings_json")
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_preview_upload",
        project_uri=project_uri,
        actor_uri=owner_uri,
    )
    return await boqpeg_service.preview_upload(
        file=file,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        bridge_mappings=bridge_mappings,
        dto_role=_resolve_identity_dto_role(identity),
    )


@router.post("/boqpeg/import-async")
async def import_boqpeg_upload_async(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    project_id: str = Form(""),
    boq_root_uri: str = Form(""),
    norm_context_root_uri: str = Form(""),
    owner_uri: str = Form(""),
    bridge_mappings_json: str = Form(""),
    commit: bool = Form(True),
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    bridge_mappings = _parse_json_object(bridge_mappings_json, field_name="bridge_mappings_json")
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_import_upload_async",
        project_uri=project_uri,
        actor_uri=owner_uri,
    )
    return await boqpeg_service.import_upload_async(
        file=file,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        bridge_mappings=bridge_mappings,
        commit=commit,
    )


@router.get("/boqpeg/import-job/{job_id}")
async def get_boqpeg_import_job(
    job_id: str,
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    return await boqpeg_service.get_import_job(job_id=job_id)


@public_router.get("/boqpeg/import-job-public/{job_id}")
async def get_boqpeg_import_job_public(
    job_id: str,
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    return await boqpeg_service.get_import_job(job_id=job_id)


@router.get("/boqpeg/import-job-active")
async def get_boqpeg_import_job_active(
    project_uri: str,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_read(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_import_job_active",
        project_uri=project_uri,
    )
    return await boqpeg_service.get_active_import_job(project_uri=project_uri)


@public_router.get("/boqpeg/import-job-active-public")
async def get_boqpeg_import_job_active_public(
    project_uri: str,
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    return await boqpeg_service.get_active_import_job(project_uri=project_uri)


@router.post("/boqpeg/engine/parse")
async def parse_boqpeg_engine_rows(
    file: UploadFile = File(...),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    return await boqpeg_service.engine_parse(file=file)


@router.post("/boqpeg/engine/forward-bom")
async def run_boqpeg_forward_bom(
    body: dict[str, Any] = Body(...),
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_forward_bom",
        body=body,
    )
    return await boqpeg_service.forward_bom(body=body)


@router.post("/boqpeg/engine/reverse-conservation")
async def run_boqpeg_reverse_conservation(
    body: dict[str, Any] = Body(...),
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_reverse_conservation",
        body=body,
    )
    return await boqpeg_service.reverse_conservation(body=body)


@router.post("/boqpeg/engine/payment-progress")
async def run_boqpeg_payment_progress(
    body: dict[str, Any] = Body(...),
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_payment_progress",
        body=body,
    )
    return await boqpeg_service.progress_payment(body=body)


@router.post("/boqpeg/engine/unified-align")
async def run_boqpeg_unified_align(
    body: dict[str, Any] = Body(...),
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_unified_align",
        body=body,
    )
    return await boqpeg_service.unified_alignment(body=body)


@router.post("/boqpeg/engine/design/parse")
async def parse_design_manifest(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    design_root_uri: str = Form(""),
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_design_parse",
        project_uri=project_uri,
        node_uri=design_root_uri,
    )
    return await boqpeg_service.parse_design_manifest(
        file=file,
        project_uri=project_uri,
        design_root_uri=design_root_uri,
    )


@router.post("/boqpeg/engine/design-boq/match")
async def match_design_boq(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    design_manifest_json: str = Form(...),
    owner_uri: str = Form(""),
    deviation_warning_ratio: float = Form(0.03),
    deviation_review_ratio: float = Form(0.08),
    threshold_spec_uri: str = Form(""),
    commit: bool = Form(False),
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    try:
        design_manifest = json.loads(design_manifest_json)
    except Exception as exc:
        raise HTTPException(400, f"invalid design_manifest_json: {exc}") from exc
    if not isinstance(design_manifest, dict):
        raise HTTPException(400, "design_manifest_json must decode to object")
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_design_boq_match",
        project_uri=project_uri,
        actor_uri=owner_uri,
    )
    return await boqpeg_service.match_design_boq(
        file=file,
        project_uri=project_uri,
        owner_uri=owner_uri,
        design_manifest=design_manifest,
        deviation_warning_ratio=deviation_warning_ratio,
        deviation_review_ratio=deviation_review_ratio,
        threshold_spec_uri=threshold_spec_uri,
        commit=commit,
    )


@router.post("/boqpeg/engine/design-boq/closure")
async def run_design_boq_bidirectional_closure(
    body: dict[str, Any] = Body(...),
    commit: bool = False,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_design_boq_closure",
        body=body,
    )
    return await boqpeg_service.bidirectional_closure(body=body, commit=bool(commit))


@router.post("/boqpeg/bridge/entity")
async def create_bridge_entity(
    body: dict[str, Any] = Body(...),
    commit: bool = False,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_create_bridge_entity",
        body=body,
    )
    return await boqpeg_service.create_bridge_entity(body=body, commit=bool(commit))


@router.post("/boqpeg/bridge/bind-sub-items")
async def bind_bridge_sub_items(
    body: dict[str, Any] = Body(...),
    commit: bool = False,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_bind_bridge_sub_items",
        body=body,
    )
    return await boqpeg_service.bind_bridge_items(body=body, commit=bool(commit))


@router.post("/boqpeg/pile/entity")
async def create_pile_entity(
    body: dict[str, Any] = Body(...),
    commit: bool = False,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_create_pile_entity",
        body=body,
    )
    return await boqpeg_service.create_pile_entity(body=body, commit=bool(commit))


@router.post("/boqpeg/pile/state")
async def update_pile_state(
    body: dict[str, Any] = Body(...),
    commit: bool = False,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_update_pile_state",
        body=body,
    )
    return await boqpeg_service.update_pile_state(body=body, commit=bool(commit))


@router.get("/boqpeg/bridge/{bridge_name}/pile/{pile_id}")
async def get_pile_entity(
    bridge_name: str,
    pile_id: str,
    project_uri: str,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_read(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_get_pile_entity",
        project_uri=project_uri,
        node_uri=f"{project_uri.rstrip('/')}/bridge/{bridge_name}/pile/{pile_id}",
    )
    return await boqpeg_service.get_pile_entity(project_uri=project_uri, bridge_name=bridge_name, pile_id=pile_id)


@router.get("/boqpeg/project/full-line/piles")
async def get_project_full_line_piles(
    project_uri: str,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_read(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_full_line_piles",
        project_uri=project_uri,
    )
    return await boqpeg_service.full_line_piles(project_uri=project_uri)


@router.get("/boqpeg/bridge/{bridge_name}/piles")
async def get_bridge_piles(
    bridge_name: str,
    project_uri: str,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_read(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_bridge_piles",
        project_uri=project_uri,
        node_uri=f"{project_uri.rstrip('/')}/bridge/{bridge_name}",
    )
    return await boqpeg_service.bridge_piles(project_uri=project_uri, bridge_name=bridge_name)


@router.post("/boqpeg/bridge/{bridge_name}/schedule")
async def create_bridge_schedule(
    bridge_name: str,
    body: dict[str, Any] = Body(...),
    commit: bool = False,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    project_uri = _to_text(body.get("project_uri")).strip()
    if not project_uri:
        raise HTTPException(400, "project_uri is required in request body")
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_create_bridge_schedule",
        project_uri=project_uri,
        node_uri=f"{project_uri.rstrip('/')}/bridge/{bridge_name}/schedule",
        body=body,
    )
    return await boqpeg_service.create_bridge_schedule(
        project_uri=project_uri,
        bridge_name=bridge_name,
        body=body,
        commit=bool(commit),
    )


@router.get("/boqpeg/bridge/{bridge_name}/schedule")
async def get_bridge_schedule(
    bridge_name: str,
    project_uri: str,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_read(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_get_bridge_schedule",
        project_uri=project_uri,
        node_uri=f"{project_uri.rstrip('/')}/bridge/{bridge_name}/schedule",
    )
    return await boqpeg_service.get_bridge_schedule(project_uri=project_uri, bridge_name=bridge_name)


@router.post("/boqpeg/bridge/{bridge_name}/schedule/sync")
async def sync_bridge_schedule(
    bridge_name: str,
    body: dict[str, Any] = Body(...),
    commit: bool = False,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    project_uri = _to_text(body.get("project_uri")).strip()
    if not project_uri:
        raise HTTPException(400, "project_uri is required in request body")
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_sync_bridge_schedule",
        project_uri=project_uri,
        node_uri=f"{project_uri.rstrip('/')}/bridge/{bridge_name}/schedule",
        body=body,
    )
    return await boqpeg_service.sync_bridge_schedule(
        project_uri=project_uri,
        bridge_name=bridge_name,
        body=body,
        commit=bool(commit),
    )


@router.get("/boqpeg/project/full-line/schedule")
async def get_project_full_line_schedule(
    project_uri: str,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_read(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_full_line_schedule",
        project_uri=project_uri,
        node_uri=f"{project_uri.rstrip('/')}/full-line/schedule",
    )
    return await boqpeg_service.full_line_schedule(project_uri=project_uri)


@router.post("/boqpeg/bridge/{bridge_name}/pile/{pile_id}/process-chain")
async def create_pile_process_chain(
    bridge_name: str,
    pile_id: str,
    body: dict[str, Any] = Body(...),
    commit: bool = False,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    payload = _as_dict(body)
    project_uri = _to_text(payload.get("project_uri")).strip()
    if not project_uri:
        raise HTTPException(400, "project_uri is required in request body")
    payload["bridge_name"] = bridge_name
    payload["pile_id"] = pile_id
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_create_process_chain",
        project_uri=project_uri,
        node_uri=f"{project_uri.rstrip('/')}/bridge/{bridge_name}/pile/{pile_id}/process-chain/main",
        body=payload,
    )
    return await boqpeg_service.create_process_chain(body=payload, commit=bool(commit))


@router.get("/boqpeg/bridge/{bridge_name}/pile/{pile_id}/process-chain")
async def get_pile_process_chain(
    bridge_name: str,
    pile_id: str,
    project_uri: str,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    component_uri = f"{project_uri.rstrip('/')}/bridge/{bridge_name}/pile/{pile_id}"
    _enforce_docpeg_read(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_get_process_chain",
        project_uri=project_uri,
        node_uri=f"{component_uri}/process-chain/main",
    )
    return await boqpeg_service.get_process_chain(
        project_uri=project_uri,
        component_uri=component_uri,
    )


@router.post("/boqpeg/bridge/{bridge_name}/pile/{pile_id}/process-chain/submit-table")
async def submit_pile_process_table(
    bridge_name: str,
    pile_id: str,
    body: dict[str, Any] = Body(...),
    commit: bool = False,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    payload = _as_dict(body)
    project_uri = _to_text(payload.get("project_uri")).strip()
    if not project_uri:
        raise HTTPException(400, "project_uri is required in request body")
    payload["bridge_name"] = bridge_name
    payload["pile_id"] = pile_id
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_submit_process_table",
        project_uri=project_uri,
        node_uri=f"{project_uri.rstrip('/')}/bridge/{bridge_name}/pile/{pile_id}/process-chain/main",
        body=payload,
    )
    return await boqpeg_service.submit_process_table(body=payload, commit=bool(commit))


@router.post("/product/mvp/phase1/bridge-pile-report")
async def generate_boqpeg_phase1_bridge_report(
    body: dict[str, Any] = Body(...),
    commit: bool = False,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_phase1_bridge_report",
        body=body,
    )
    return await boqpeg_service.phase1_bridge_report(body=body, commit=bool(commit))


@router.post("/product/normref/logic-scaffold")
async def bootstrap_normref_logic_scaffold(
    body: dict[str, Any] = Body(default_factory=dict),
    commit: bool = False,
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_normref_logic_scaffold",
        project_uri="v://normref.com",
        actor_uri=_to_text(_as_dict(body).get("owner_uri")).strip() or "v://normref.com/executor/system/",
    )
    payload = _as_dict(body)
    if not payload.get("owner_uri"):
        payload["owner_uri"] = "v://normref.com/executor/system/"
    return await boqpeg_service.normref_logic_scaffold(body=payload, commit=bool(commit))


@router.post("/product/normref/tab-to-peg")
async def run_normref_tab_to_peg(
    file: UploadFile = File(...),
    protocol_uri: str = Form(""),
    norm_code: str = Form(""),
    boq_item_id: str = Form(""),
    project_ref: str = Form(""),
    component_id: str = Form(""),
    drawing_ref: str = Form(""),
    structured_data_json: str = Form(""),
    description: str = Form(""),
    bridge_uri: str = Form(""),
    component_type: str = Form(""),
    topology_component_count: int = Form(0),
    forms_per_component: int = Form(2),
    generated_qc_table_count: int = Form(0),
    signed_pass_table_count: int = Form(0),
    owner_uri: str = Form("v://normref.com/executor/system/"),
    commit: bool = Form(False),
    identity: dict[str, Any] = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    _enforce_docpeg_write(
        gate=docpeg_gate,
        identity=identity,
        operation="boqpeg_normref_tab_to_peg",
        project_uri="v://normref.com",
        node_uri=protocol_uri or "v://normref.com/schema/qc-v1",
        actor_uri=owner_uri,
    )
    structured_data = _parse_json_object(structured_data_json, field_name="structured_data_json")
    return await boqpeg_service.tab_to_peg(
        file=file,
        protocol_uri=protocol_uri,
        norm_code=norm_code,
        boq_item_id=boq_item_id,
        project_ref=project_ref,
        component_id=component_id,
        drawing_ref=drawing_ref,
        structured_data=structured_data,
        description=description,
        bridge_uri=bridge_uri,
        component_type=component_type,
        topology_component_count=int(topology_component_count or 0),
        forms_per_component=int(forms_per_component or 2),
        generated_qc_table_count=int(generated_qc_table_count or 0),
        signed_pass_table_count=int(signed_pass_table_count or 0),
        owner_uri=owner_uri,
        commit=bool(commit),
    )

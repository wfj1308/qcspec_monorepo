"""
Flow helpers for proof router.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import mimetypes
import re
from typing import Any
from uuid import UUID
import uuid
import zipfile

import httpx
from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
import io
from supabase import Client

from services.api.domain.boq.helpers import (
    download_evidence_center_zip as domain_download_evidence_center_zip,
    get_evidence_center_evidence as domain_get_evidence_center_evidence,
    project_readiness_check as domain_project_readiness_check,
)
from services.api.domain.proof.helpers import (
    download_docfinal_zip as domain_download_docfinal_zip,
    export_doc_final_package as domain_export_doc_final_package,
    finalize_docfinal_delivery_package as domain_finalize_docfinal_delivery_package,
    get_docfinal_context as domain_get_docfinal_context,
    replay_offline_packets_payload as domain_replay_offline_packets_payload,
)
from services.api.domain.proof.service import ProofApplicationService
from services.api.proof_utxo_engine import ProofUTXOEngine
from services.api.boq_payment_audit_service import (
    audit_trace,
    generate_railpact_instruction,
    generate_payment_certificate,
)
from services.api.labpeg_frequency_remediation_service import (
    calc_inspection_frequency,
    close_remediation_trip,
    get_frequency_dashboard,
    open_remediation_trip,
    record_lab_test,
    remediation_reinspect,
)
from services.api.spatial_ai_finance_service import (
    bind_utxo_to_spatial,
    export_finance_proof,
    get_spatial_dashboard,
    predictive_quality_analysis,
)
from services.api.rwa_om_evolution_service import (
    convert_to_finance_asset,
    export_sovereign_om_bundle,
    generate_norm_evolution_report,
    register_om_event,
)
from services.api.triprole_engine import (
    aggregate_provenance_chain,
    apply_variation,
    execute_triprole_action,
    get_full_lineage,
    trace_asset_origin,
    get_boq_realtime_status,
    ingest_sensor_data,
    scan_to_confirm_signature,
    transfer_asset,
)
from services.api.did_reputation_service import compute_did_reputation
from services.api.gate_rule_editor_service import (
    generate_rules_via_ai,
    get_gate_editor_payload,
    import_from_norm_library,
    rollback_gate_rule,
    save_gate_rule_version,
)
from services.api.unit_merkle_service import build_unit_merkle_snapshot
from services.api.specdict_gate_service import (
    get_spec_dict,
    resolve_dynamic_threshold,
    save_spec_dict,
)
from services.api.doc_governance_service import (
    auto_classify_document,
    auto_generate_stake_nodes,
    create_node,
    list_node_tree,
    register_document,
    search_documents,
)
from services.api.boq_audit_engine_service import (
    get_item_sovereign_history,
    run_boq_audit_engine,
)
from services.api.specdict_evolution_service import (
    analyze_specdict_evolution,
    export_specdict_bundle,
)
from services.api.ar_anchor_service import get_ar_anchor_overlay
from services.api.smu_flow_service import (
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
from services.api.smu_import_job_service import (
    get_active_smu_import_job,
    get_smu_import_job,
    start_smu_import_job,
)


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except Exception:
        return False


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
        return float(match.group(0)) if match else None


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


def _safe_name(value: str, default: str = "file.bin") -> str:
    text = str(value or "").strip()
    if not text:
        return default
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", text)
    return safe[:180] or default


def _parse_json_dict(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except Exception:
        pass
    return {}


def _parse_tags(raw: str) -> list[str]:
    text = str(raw or "").strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            value = json.loads(text)
            if isinstance(value, list):
                return [str(x).strip() for x in value if str(x).strip()]
        except Exception:
            pass
    return [x.strip() for x in text.split(",") if x.strip()]


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _status(complete: bool, partial: bool) -> str:
    if complete:
        return "complete"
    if partial:
        return "partial"
    return "missing"


def _extract_text_excerpt(content: bytes, mime_type: str, max_chars: int = 2000) -> str:
    if not content:
        return ""
    mt = str(mime_type or "").lower()
    if mt.startswith("text/") or mt in {"application/json", "application/xml"}:
        return content[: max_chars * 2].decode("utf-8", errors="replace")[:max_chars]
    return ""


def _chain_root_hash(fingerprints: list[dict[str, Any]]) -> str:
    canonical = json.dumps(fingerprints, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _fetch_binary(url: str, timeout_s: float = 10.0) -> bytes | None:
    target = _to_text(url).strip()
    if not target or not (target.startswith("http://") or target.startswith("https://")):
        return None
    try:
        res = httpx.get(target, timeout=timeout_s)
        if res.status_code >= 400:
            return None
        return res.content
    except Exception:
        return None


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


def execute_triprole_action_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return execute_triprole_action(sb=sb, body=body)


def aggregate_provenance_chain_flow(*, utxo_id: str, sb: Client) -> dict[str, Any]:
    return aggregate_provenance_chain(utxo_id=utxo_id, sb=sb)


def get_full_lineage_flow(*, utxo_id: str, sb: Client) -> dict[str, Any]:
    return get_full_lineage(utxo_id=utxo_id, sb=sb)


def trace_asset_origin_flow(
    *,
    sb: Client,
    utxo_id: str = "",
    boq_item_uri: str = "",
    project_uri: str = "",
) -> dict[str, Any]:
    return trace_asset_origin(
        sb=sb,
        utxo_id=utxo_id,
        boq_item_uri=boq_item_uri,
        project_uri=project_uri,
    )


def did_reputation_flow(
    *,
    sb: Client,
    project_uri: str,
    participant_did: str,
    window_days: int = 90,
) -> dict[str, Any]:
    return compute_did_reputation(
        sb=sb,
        project_uri=project_uri,
        participant_did=participant_did,
        window_days=window_days,
    )


def transfer_asset_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return transfer_asset(
        sb=sb,
        item_id=str(body.item_id or ""),
        amount=float(body.amount),
        project_uri=str(body.project_uri or ""),
        executor_uri=str(body.executor_uri or "v://executor/system/"),
        executor_role=str(body.executor_role or "DOCPEG"),
        docpeg_proof_id=str(body.docpeg_proof_id or ""),
        docpeg_hash=str(body.docpeg_hash or ""),
        metadata=dict(body.metadata or {}),
    )


def apply_variation_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return apply_variation(
        sb=sb,
        boq_item_uri=str(body.boq_item_uri or ""),
        delta_amount=float(body.delta_amount),
        reason=str(body.reason or ""),
        project_uri=str(body.project_uri or ""),
        executor_uri=str(body.executor_uri or "v://executor/system/"),
        executor_did=str(body.executor_did or ""),
        executor_role=str(body.executor_role or "TRIPROLE"),
        metadata=dict(body.metadata or {}),
        credentials_vc=list(body.credentials_vc or []),
        geo_location=dict(body.geo_location or {}),
        server_timestamp_proof=dict(body.server_timestamp_proof or {}),
        offline_packet_id=str(body.offline_packet_id or ""),
    )


def replay_offline_packets_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return domain_replay_offline_packets_payload(body=body, sb=sb)


def scan_confirm_signature_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return scan_to_confirm_signature(
        sb=sb,
        input_proof_id=str(body.input_proof_id or ""),
        scan_payload=str(body.scan_payload or ""),
        scanner_did=str(body.scanner_did or ""),
        scanner_role=str(body.scanner_role or "supervisor"),
        executor_uri=str(body.executor_uri or "v://executor/system/"),
        executor_role=str(body.executor_role or "SUPERVISOR"),
        signature_hash=str(body.signature_hash or ""),
        signer_metadata=dict(body.signer_metadata or {}),
        geo_location=dict(body.geo_location or {}),
        server_timestamp_proof=dict(body.server_timestamp_proof or {}),
    )


def ingest_sensor_data_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return ingest_sensor_data(
        sb=sb,
        device_id=str(body.device_id or ""),
        raw_payload=body.raw_payload,
        boq_item_uri=str(body.boq_item_uri or ""),
        project_uri=str(body.project_uri or "") or None,
        executor_uri=str(body.executor_uri or "v://executor/system/"),
        executor_did=str(body.executor_did or ""),
        executor_role=str(body.executor_role or "TRIPROLE"),
        metadata=dict(body.metadata or {}),
        credentials_vc=list(body.credentials_vc or []),
        geo_location=dict(body.geo_location or {}),
        server_timestamp_proof=dict(body.server_timestamp_proof or {}),
    )


def get_unit_merkle_root_flow(
    *,
    project_uri: str,
    unit_code: str,
    proof_id: str,
    max_rows: int,
    sb: Client,
) -> dict[str, Any]:
    return build_unit_merkle_snapshot(
        sb=sb,
        project_uri=project_uri,
        unit_code=unit_code,
        proof_id=proof_id,
        max_rows=max_rows,
    )


def get_docfinal_context_flow(
    *,
    boq_item_uri: str,
    project_name: str | None,
    verify_base_url: str,
    template_path: str | None,
    aggregate_anchor_code: str,
    aggregate_direction: str,
    aggregate_level: str,
    sb: Client,
) -> dict[str, Any]:
    return domain_get_docfinal_context(
        boq_item_uri=boq_item_uri,
        project_name=project_name,
        verify_base_url=verify_base_url,
        template_path=template_path,
        aggregate_anchor_code=aggregate_anchor_code,
        aggregate_direction=aggregate_direction,
        aggregate_level=aggregate_level,
        sb=sb,
    )


async def download_docfinal_zip_flow(
    *,
    boq_item_uri: str,
    project_name: str | None,
    verify_base_url: str,
    template_path: str | None,
    aggregate_anchor_code: str,
    aggregate_direction: str,
    aggregate_level: str,
    sb: Client,
) -> StreamingResponse:
    return await domain_download_docfinal_zip(
        boq_item_uri=boq_item_uri,
        project_name=project_name,
        verify_base_url=verify_base_url,
        template_path=template_path,
        aggregate_anchor_code=aggregate_anchor_code,
        aggregate_direction=aggregate_direction,
        aggregate_level=aggregate_level,
        sb=sb,
    )


async def download_evidence_center_zip_flow(
    *,
    project_uri: str,
    subitem_code: str,
    proof_id: str | None,
    sb: Client,
    verify_base_url: str = "https://verify.qcspec.com",
) -> StreamingResponse:
    return await domain_download_evidence_center_zip(
        project_uri=project_uri,
        subitem_code=subitem_code,
        proof_id=proof_id,
        sb=sb,
        verify_base_url=verify_base_url,
    )


def get_evidence_center_evidence_flow(
    *,
    project_uri: str | None,
    subitem_code: str | None,
    boq_item_uri: str | None,
    smu_id: str | None,
    sb: Client,
) -> dict[str, Any]:
    return domain_get_evidence_center_evidence(
        project_uri=project_uri,
        subitem_code=subitem_code,
        boq_item_uri=boq_item_uri,
        smu_id=smu_id,
        sb=sb,
    )


def get_boq_realtime_status_flow(
    *,
    project_uri: str,
    sb: Client,
) -> dict[str, Any]:
    return get_boq_realtime_status(sb=sb, project_uri=project_uri)


async def export_doc_final_flow(
    *,
    body: Any,
    sb: Client,
) -> StreamingResponse:
    return await domain_export_doc_final_package(body=body, sb=sb)


def generate_payment_certificate_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return generate_payment_certificate(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        period=str(body.period or ""),
        project_name=str(body.project_name or ""),
        verify_base_url=str(body.verify_base_url or "https://verify.qcspec.com"),
        create_proof=bool(body.create_proof),
        executor_uri=str(body.executor_uri or "v://executor/system/"),
        enforce_dual_pass=bool(body.enforce_dual_pass if body.enforce_dual_pass is not None else True),
    )


def audit_trace_flow(
    *,
    payment_id: str,
    verify_base_url: str,
    sb: Client,
) -> dict[str, Any]:
    return audit_trace(
        sb=sb,
        payment_id=payment_id,
        verify_base_url=verify_base_url,
    )


def record_lab_test_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return record_lab_test(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        boq_item_uri=str(body.boq_item_uri or ""),
        sample_id=str(body.sample_id or ""),
        jtg_form_code=str(body.jtg_form_code or "JTG-E60"),
        instrument_sn=str(body.instrument_sn or ""),
        tested_at=str(body.tested_at or ""),
        witness_record=dict(body.witness_record or {}),
        sample_tracking=dict(body.sample_tracking or {}),
        metrics=list(body.metrics or []),
        result=str(body.result or ""),
        executor_uri=str(body.executor_uri or "v://executor/lab/system/"),
        metadata=dict(body.metadata or {}),
    )


def calc_inspection_frequency_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return calc_inspection_frequency(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        boq_item_uri=str(body.boq_item_uri or ""),
    )


def get_frequency_dashboard_flow(*, project_uri: str, limit_items: int, sb: Client) -> dict[str, Any]:
    return get_frequency_dashboard(
        sb=sb,
        project_uri=project_uri,
        limit_items=limit_items,
    )


def open_remediation_trip_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return open_remediation_trip(
        sb=sb,
        fail_proof_id=str(body.fail_proof_id or ""),
        notice=str(body.notice or ""),
        executor_uri=str(body.executor_uri or "v://executor/supervisor/system/"),
        due_date=str(body.due_date or ""),
        assignees=list(body.assignees or []),
    )


def remediation_reinspect_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return remediation_reinspect(
        sb=sb,
        remediation_proof_id=str(body.remediation_proof_id or ""),
        result=str(body.result or ""),
        payload=dict(body.payload or {}),
        executor_uri=str(body.executor_uri or "v://executor/inspector/system/"),
    )


def close_remediation_trip_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return close_remediation_trip(
        sb=sb,
        remediation_proof_id=str(body.remediation_proof_id or ""),
        reinspection_proof_id=str(body.reinspection_proof_id or ""),
        close_note=str(body.close_note or ""),
        executor_uri=str(body.executor_uri or "v://executor/supervisor/system/"),
    )


def generate_railpact_instruction_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return generate_railpact_instruction(
        sb=sb,
        payment_id=str(body.payment_id or ""),
        executor_uri=str(body.executor_uri or "v://executor/owner/system/"),
        auto_submit=bool(body.auto_submit),
    )


async def finalize_docfinal_delivery_flow(
    *,
    body: Any,
    sb: Client,
) -> StreamingResponse:
    return await domain_finalize_docfinal_delivery_package(body=body, sb=sb)


def bind_utxo_to_spatial_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return bind_utxo_to_spatial(
        sb=sb,
        utxo_id=str(body.utxo_id or ""),
        bim_id=str(body.bim_id or ""),
        coordinate=dict(body.coordinate or {}),
        project_uri=str(body.project_uri or ""),
        label=str(body.label or ""),
        metadata=dict(body.metadata or {}),
    )


def get_spatial_dashboard_flow(*, project_uri: str, limit: int, sb: Client) -> dict[str, Any]:
    return get_spatial_dashboard(
        sb=sb,
        project_uri=project_uri,
        limit=limit,
    )


def predictive_quality_analysis_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return predictive_quality_analysis(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        near_threshold_ratio=float(body.near_threshold_ratio or 0.9),
        min_samples=int(body.min_samples or 3),
        apply_dynamic_gate=bool(body.apply_dynamic_gate),
        default_critical_threshold=float(body.default_critical_threshold or 2.0),
    )


async def export_finance_proof_flow(*, body: Any, sb: Client) -> StreamingResponse:
    result = export_finance_proof(
        sb=sb,
        payment_id=str(body.payment_id or ""),
        bank_code=str(body.bank_code or ""),
        passphrase=str(body.passphrase or ""),
        run_anchor_rounds=int(body.run_anchor_rounds or 0),
    )
    return StreamingResponse(
        io.BytesIO(result.get("blob_bytes") or b""),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{result.get("filename") or "FINANCE-PROOF.qcfp"}"',
            "X-Finance-Payment-Id": str(result.get("payment_id") or ""),
            "X-Finance-Proof-Id": str(result.get("finance_proof_id") or ""),
            "X-Finance-Payload-Hash": str(result.get("payload_hash") or ""),
            "X-Finance-GitPeg-Anchor": str(result.get("finance_gitpeg_anchor") or ""),
        },
    )


async def convert_to_finance_asset_flow(*, body: Any, sb: Client) -> StreamingResponse:
    result = convert_to_finance_asset(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        boq_group_id=str(body.boq_group_id or ""),
        project_name=str(body.project_name or ""),
        bank_code=str(body.bank_code or ""),
        passphrase=str(body.passphrase or ""),
        run_anchor_rounds=int(body.run_anchor_rounds or 0),
    )
    return StreamingResponse(
        io.BytesIO(result.get("blob_bytes") or b""),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{result.get("filename") or "RWA-ASSET.qcrwa"}"',
            "X-RWA-Project-Uri": str(result.get("project_uri") or ""),
            "X-RWA-Group-Id": str(result.get("boq_group_id") or ""),
            "X-RWA-Proof-Id": str(result.get("rwa_proof_id") or ""),
            "X-RWA-Certificate-Hash": str(result.get("certificate_hash") or ""),
            "X-RWA-GitPeg-Anchor": str(result.get("rwa_gitpeg_anchor") or ""),
        },
    )


async def export_sovereign_om_bundle_flow(*, body: Any, sb: Client) -> StreamingResponse:
    result = export_sovereign_om_bundle(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        project_name=str(body.project_name or ""),
        om_owner_uri=str(body.om_owner_uri or "v://operator/om/default"),
        passphrase=str(body.passphrase or ""),
        run_anchor_rounds=int(body.run_anchor_rounds or 0),
    )
    return StreamingResponse(
        io.BytesIO(result.get("zip_bytes") or b""),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{result.get("filename") or "OM-HANDOVER.zip"}"',
            "X-OM-Root-Uri": str(result.get("om_root_uri") or ""),
            "X-OM-Root-Proof-Id": str(result.get("om_root_proof_id") or ""),
            "X-OM-GitPeg-Anchor": str(result.get("om_gitpeg_anchor") or ""),
            "X-OM-Payload-Hash": str(result.get("payload_hash") or ""),
        },
    )


def register_om_event_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return register_om_event(
        sb=sb,
        om_root_proof_id=str(body.om_root_proof_id or ""),
        title=str(body.title or ""),
        event_type=str(body.event_type or "maintenance"),
        payload=dict(body.payload or {}),
        executor_uri=str(body.executor_uri or "v://operator/om/default"),
    )


def specdict_evolution_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return analyze_specdict_evolution(
        sb=sb,
        project_uris=list(body.project_uris or []),
        min_samples=int(body.min_samples or 5),
    )


def specdict_export_bundle_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return export_specdict_bundle(
        sb=sb,
        project_uris=list(body.project_uris or []),
        min_samples=int(body.min_samples or 5),
        namespace_uri=str(body.namespace_uri or "v://global/templates"),
        commit=bool(body.commit),
    )


def ar_anchor_overlay_flow(
    *,
    project_uri: str,
    lat: float,
    lng: float,
    radius_m: float,
    limit: int,
    sb: Client,
) -> dict[str, Any]:
    return get_ar_anchor_overlay(
        sb=sb,
        project_uri=project_uri,
        lat=lat,
        lng=lng,
        radius_m=radius_m,
        limit=limit,
    )


def generate_norm_evolution_report_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return generate_norm_evolution_report(
        sb=sb,
        project_uris=list(body.project_uris or []),
        min_samples=int(body.min_samples or 5),
        near_threshold_ratio=float(body.near_threshold_ratio or 0.9),
        anonymize=bool(body.anonymize),
        create_proof=bool(body.create_proof),
    )


def get_gate_editor_payload_flow(
    *,
    project_uri: str,
    subitem_code: str,
    sb: Client,
) -> dict[str, Any]:
    return get_gate_editor_payload(
        sb=sb,
        project_uri=project_uri,
        subitem_code=subitem_code,
    )


def import_gate_rules_from_norm_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return import_from_norm_library(
        sb=sb,
        spec_uri=str(body.spec_uri or ""),
        context=str(body.context or ""),
    )


def generate_gate_rules_via_ai_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return generate_rules_via_ai(
        prompt=str(body.prompt or ""),
        subitem_code=str(body.subitem_code or ""),
    )


def save_gate_rule_version_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return save_gate_rule_version(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        subitem_code=str(body.subitem_code or ""),
        gate_id_base=str(body.gate_id_base or ""),
        rules=list(body.rules or []),
        execution_strategy=str(body.execution_strategy or "all_pass"),
        fail_action=str(body.fail_action or "trigger_review_trip"),
        apply_to_similar=bool(body.apply_to_similar),
        executor_uri=str(body.executor_uri or "v://executor/chief-engineer/"),
        metadata=dict(body.metadata or {}),
    )


def rollback_gate_rule_version_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return rollback_gate_rule(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        subitem_code=str(body.subitem_code or ""),
        target_proof_id=str(body.target_proof_id or ""),
        target_version=str(body.target_version or ""),
        apply_to_similar=bool(body.apply_to_similar),
        executor_uri=str(body.executor_uri or "v://executor/chief-engineer/"),
    )


def get_spec_dict_flow(*, spec_dict_key: str, sb: Client) -> dict[str, Any]:
    return get_spec_dict(
        sb=sb,
        spec_dict_key=spec_dict_key,
    )


def save_spec_dict_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return save_spec_dict(
        sb=sb,
        spec_dict_key=str(body.spec_dict_key or ""),
        title=str(body.title or ""),
        version=str(body.version or "v1.0"),
        authority=str(body.authority or ""),
        spec_uri=str(body.spec_uri or ""),
        items=dict(body.items or {}),
        metadata=dict(body.metadata or {}),
        is_active=bool(body.is_active if body.is_active is not None else True),
    )


def resolve_dynamic_threshold_flow(*, gate_id: str, context: str, sb: Client) -> dict[str, Any]:
    return resolve_dynamic_threshold(
        sb=sb,
        gate_id=gate_id,
        context={"context": context},
    )


async def doc_auto_classify_flow(*, body: Any) -> dict[str, Any]:
    payload = await auto_classify_document(
        file_name=str(body.file_name or ""),
        text_excerpt=str(body.text_excerpt or ""),
        mime_type=str(body.mime_type or ""),
    )
    return {"ok": True, "suggestion": payload}


def doc_create_node_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return create_node(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        parent_uri=str(body.parent_uri or ""),
        node_name=str(body.node_name or ""),
        executor_uri=str(body.executor_uri or "v://executor/system/"),
        metadata=dict(body.metadata or {}),
    )


def doc_auto_generate_nodes_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return auto_generate_stake_nodes(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        parent_uri=str(body.parent_uri or "") or str(body.project_uri or ""),
        start_km=int(body.start_km),
        end_km=int(body.end_km),
        step_km=int(body.step_km or 1),
        leaf_name=str(body.leaf_name or "inspection"),
        executor_uri=str(body.executor_uri or "v://executor/system/"),
    )


def doc_tree_flow(*, project_uri: str, root_uri: str, sb: Client) -> dict[str, Any]:
    return list_node_tree(
        sb=sb,
        project_uri=project_uri,
        root_uri=root_uri,
    )


def doc_search_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return search_documents(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        node_uri=str(body.node_uri or ""),
        include_descendants=bool(body.include_descendants),
        query=str(body.query or ""),
        tags=list(body.tags or []),
        field_filters=dict(body.field_filters or {}),
        limit=int(body.limit or 200),
    )


async def doc_register_upload_flow(
    *,
    file: UploadFile,
    project_uri: str,
    node_uri: str,
    source_utxo_id: str,
    executor_uri: str,
    text_excerpt: str,
    tags: str,
    custom_metadata: str,
    ai_metadata: str,
    auto_classify: bool,
    sb: Client,
) -> dict[str, Any]:
    content = await file.read()
    if not content:
        raise HTTPException(400, "empty file")
    if len(content) > 200 * 1024 * 1024:
        raise HTTPException(400, "file too large, max 200MB")

    mime_type = str(file.content_type or "application/octet-stream").strip().lower()
    file_name = _safe_name(file.filename or "document.bin")
    now = datetime.now(timezone.utc)
    project_key = _safe_name(project_uri.replace("v://", "v_"), "project")
    storage_path = (
        f"{project_key}/docs/{now.strftime('%Y%m%d')}/"
        f"{now.strftime('%H%M%S')}_{uuid.uuid4().hex[:8]}_{file_name}"
    )
    sb.storage.from_("qcspec-reports").upload(
        storage_path,
        content,
        file_options={"content-type": mime_type or "application/octet-stream"},
    )
    public_url = sb.storage.from_("qcspec-reports").get_public_url(storage_path)
    storage_url = public_url if isinstance(public_url, str) else ""

    excerpt = str(text_excerpt or "").strip()
    if not excerpt:
        excerpt = _extract_text_excerpt(content, mime_type)

    ai_meta = _parse_json_dict(ai_metadata)
    if auto_classify and not ai_meta:
        ai_meta = await auto_classify_document(
            file_name=file_name,
            text_excerpt=excerpt,
            mime_type=mime_type,
        )

    return register_document(
        sb=sb,
        project_uri=project_uri,
        node_uri=node_uri or project_uri,
        source_utxo_id=source_utxo_id,
        file_name=file_name,
        file_size=len(content),
        mime_type=mime_type,
        storage_path=storage_path,
        storage_url=storage_url,
        text_excerpt=excerpt,
        ai_metadata=ai_meta,
        custom_metadata=_parse_json_dict(custom_metadata),
        tags=_parse_tags(tags),
        executor_uri=executor_uri or "v://executor/system/",
    )


def boq_item_sovereign_history_flow(
    *,
    project_uri: str,
    subitem_code: str,
    max_rows: int,
    sb: Client,
) -> dict[str, Any]:
    return get_item_sovereign_history(
        sb=sb,
        project_uri=project_uri,
        subitem_code=subitem_code,
        max_rows=max_rows,
    )


def boq_reconciliation_flow(
    *,
    project_uri: str,
    subitem_code: str,
    max_rows: int,
    limit_items: int,
    sb: Client,
) -> dict[str, Any]:
    return run_boq_audit_engine(
        sb=sb,
        project_uri=project_uri,
        subitem_code=subitem_code,
        max_rows=max_rows,
        limit_items=limit_items,
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
    content = file.file.read()
    if not content:
        raise HTTPException(400, "empty upload file")
    if len(content) > 60 * 1024 * 1024:
        raise HTTPException(400, "upload file too large, max 60MB")
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
    content = file.file.read()
    if not content:
        raise HTTPException(400, "empty upload file")
    if len(content) > 60 * 1024 * 1024:
        raise HTTPException(400, "upload file too large, max 60MB")
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
    content = file.file.read()
    if not content:
        raise HTTPException(400, "empty upload file")
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


def project_readiness_check_flow(*, project_uri: str, sb: Client) -> dict[str, Any]:
    return domain_project_readiness_check(project_uri=project_uri, sb=sb)

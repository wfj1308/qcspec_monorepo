"""Pure helper functions for SMU freeze payload assembly."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from fastapi import HTTPException
from services.api.smu_primitives import (
    as_dict as _as_dict,
    to_float as _to_float,
    to_text as _to_text,
    utc_iso as _utc_iso,
)


def _sha(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def build_freeze_proof_id(*, project_uri: str, smu_id: str, total_proof_hash: str) -> str:
    freeze_seed = _sha(
        {
            "project_uri": _to_text(project_uri).strip(),
            "smu_id": _to_text(smu_id).strip(),
            "root": _to_text(total_proof_hash).strip(),
            "ts": _utc_iso(),
        }
    )[:18].upper()
    return f"GP-SMU-{freeze_seed}"


def build_freeze_state_data(
    *,
    project_uri: str,
    smu_id: str,
    status: str,
    risk_score: float,
    total_proof_hash: str,
    audit: dict[str, Any],
    qualification: dict[str, Any],
    merkle: dict[str, Any],
    executor_uri: str,
) -> dict[str, Any]:
    return {
        "asset_type": "smu_freeze",
        "status": "SMU_FROZEN" if status == "PASS" else "SMU_FREEZE_REJECTED",
        "lifecycle_stage": "SMU_FREEZE",
        "smu_id": smu_id,
        "risk_score": risk_score,
        "risk_logic_hash": _to_text(audit.get("logic_hash") or "").strip(),
        "audit_summary": audit.get("summary") or {},
        "unit_merkle_root": total_proof_hash,
        "project_root_hash": _to_text(merkle.get("project_root_hash") or merkle.get("global_project_fingerprint") or "").strip(),
        "leaf_count": merkle.get("leaf_count"),
        "total_proof_hash": total_proof_hash,
        "container": {
            "status": "Frozen" if status == "PASS" else "Blocked",
            "stage": "SMU & Risk Audit",
            "boq_item_uri": "",
            "smu_id": smu_id,
        },
        "trip": {
            "phase": "SMU.freeze",
            "pushed_to_settlement_dashboard": status == "PASS",
        },
        "role": {
            "executor_uri": executor_uri,
            "executor_role": "OWNER",
        },
        "settlement_packet": {
            "smu_id": smu_id,
            "project_uri": project_uri,
            "total_proof_hash": total_proof_hash,
            "risk_score": risk_score,
            "status": status,
            "qualified_leaf_count": int(qualification.get("qualified_leaf_count") or 0),
            "leaf_total": int(qualification.get("leaf_total") or 0),
            "created_at": _utc_iso(),
        },
    }


def build_freeze_response(
    *,
    executor_uri: str,
    status: str,
    risk_score: float,
    min_risk_score: float,
    smu_id: str,
    row: dict[str, Any],
    total_proof_hash: str,
    audit: dict[str, Any],
    immutable_result: dict[str, Any],
    merkle: dict[str, Any],
    state_data: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ok": True,
        "phase": "SMU & Risk Audit",
        "role": {
            "executor_uri": executor_uri,
            "executor_role": "OWNER",
        },
        "trip": {
            "name": "SMU.freeze()",
            "result": status,
            "risk_score": risk_score,
            "min_risk_score": min_risk_score,
        },
        "container": {
            "status": "Frozen" if status == "PASS" else "Blocked",
            "stage": "SMU & Risk Audit",
            "smu_id": smu_id,
        },
        "freeze_proof_id": _to_text(row.get("proof_id") or "").strip(),
        "total_proof_hash": total_proof_hash,
        "audit": audit,
        "immutable_update": immutable_result,
        "merkle": {
            "unit_root_hash": _to_text(merkle.get("unit_root_hash") or "").strip(),
            "project_root_hash": _to_text(merkle.get("project_root_hash") or merkle.get("global_project_fingerprint") or "").strip(),
            "leaf_count": merkle.get("leaf_count"),
        },
        "settlement_packet": _as_dict(state_data.get("settlement_packet")),
    }


def normalize_freeze_context(freeze_ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit": _as_dict(freeze_ctx.get("audit")),
        "qualification": _as_dict(freeze_ctx.get("qualification")),
        "risk_score": _to_float(freeze_ctx.get("risk_score")) or 0.0,
        "merkle": _as_dict(freeze_ctx.get("merkle")),
        "total_proof_hash": _to_text(freeze_ctx.get("total_proof_hash") or "").strip(),
        "status": _to_text(freeze_ctx.get("status") or "").strip().upper() or "FAIL",
    }


def build_freeze_proof_create_payload(
    *,
    executor_uri: str,
    project_uri: str,
    smu_id: str,
    freeze_proof_id: str,
    status: str,
    state_data: dict[str, Any],
) -> dict[str, Any]:
    executor = _to_text(executor_uri).strip() or "v://executor/owner/system/"
    p_uri = _to_text(project_uri).strip()
    s_id = _to_text(smu_id).strip()
    return {
        "proof_id": freeze_proof_id,
        "owner_uri": executor,
        "project_uri": p_uri,
        "project_id": None,
        "segment_uri": f"{p_uri.rstrip('/')}/smu/{s_id}",
        "proof_type": "smu_freeze",
        "result": status,
        "state_data": state_data,
        "conditions": [],
        "parent_proof_id": None,
        "norm_uri": "v://norm/CoordOS/SMU/1.0#freeze",
        "signer_uri": executor,
        "signer_role": "OWNER",
        "gitpeg_anchor": None,
        "anchor_config": None,
    }


def build_freeze_payloads_from_context(
    *,
    freeze_ctx: dict[str, Any],
    project_uri: str,
    smu_id: str,
    executor_uri: str,
) -> dict[str, Any]:
    values = normalize_freeze_context(freeze_ctx)
    audit = _as_dict(values.get("audit"))
    qualification = _as_dict(values.get("qualification"))
    risk_score = _to_float(values.get("risk_score")) or 0.0
    merkle = _as_dict(values.get("merkle"))
    total_proof_hash = _to_text(values.get("total_proof_hash") or "").strip()
    status = _to_text(values.get("status") or "").strip().upper() or "FAIL"
    freeze_proof_id = build_freeze_proof_id(
        project_uri=project_uri,
        smu_id=smu_id,
        total_proof_hash=total_proof_hash,
    )
    state_data = build_freeze_state_data(
        project_uri=project_uri,
        smu_id=smu_id,
        status=status,
        risk_score=risk_score,
        total_proof_hash=total_proof_hash,
        audit=audit,
        qualification=qualification,
        merkle=merkle,
        executor_uri=executor_uri,
    )
    return {
        "audit": audit,
        "qualification": qualification,
        "risk_score": risk_score,
        "merkle": merkle,
        "total_proof_hash": total_proof_hash,
        "status": status,
        "freeze_proof_id": freeze_proof_id,
        "state_data": state_data,
    }


def resolve_freeze_context(
    *,
    sb: Any,
    project_uri: str,
    smu_id: str,
    min_risk_score: float,
    is_smu_frozen: Any,
    validate_logic: Any,
    build_unit_merkle_snapshot: Any,
) -> dict[str, Any]:
    freeze_state = _as_dict(is_smu_frozen(sb=sb, project_uri=project_uri, smu_id=smu_id))
    if bool(freeze_state.get("frozen")):
        raise HTTPException(409, f"smu_already_frozen: {smu_id}")
    audit = _as_dict(validate_logic(sb=sb, project_uri=project_uri, smu_id=smu_id))
    qualification = _as_dict(audit.get("qualification"))
    if not bool(qualification.get("all_qualified")):
        pending = int(qualification.get("unqualified_leaf_count") or 0)
        raise HTTPException(409, f"freeze_blocked: {pending} leaf nodes not qualified")
    risk_score = _to_float(_as_dict(audit.get("summary")).get("risk_score")) or 0.0
    merkle = _as_dict(
        build_unit_merkle_snapshot(
            sb=sb,
            project_uri=project_uri,
            unit_code=smu_id,
            proof_id="",
            max_rows=50000,
        )
    )
    total_proof_hash = _to_text(merkle.get("unit_root_hash") or "").strip()
    if not total_proof_hash:
        raise HTTPException(409, "unit_root_hash is empty, cannot freeze")
    status = "PASS" if risk_score >= float(min_risk_score) else "FAIL"
    return {
        "audit": audit,
        "qualification": qualification,
        "risk_score": risk_score,
        "merkle": merkle,
        "total_proof_hash": total_proof_hash,
        "status": status,
    }


__all__ = [
    "build_freeze_payloads_from_context",
    "build_freeze_proof_create_payload",
    "build_freeze_proof_id",
    "build_freeze_response",
    "build_freeze_state_data",
    "normalize_freeze_context",
    "resolve_freeze_context",
]

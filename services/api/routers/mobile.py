"""Mobile QC workflow routes."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
import hashlib
import io
import json
from threading import Lock
from typing import Any
from urllib.parse import unquote
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
import qrcode
from supabase import Client

from services.api.domain.auth.runtime.auth import require_auth_user
from services.api.domain.execution.runtime.triprole_engine import execute_triprole_action
from services.api.domain.utxo.integrations import ProofUTXOEngine
from services.api.infrastructure.database import get_supabase_client

router = APIRouter()

_ROLE_SET = {"检查", "记录", "复核", "施工单位", "监理"}

_DATA_LOCK = Lock()
_WORKORDERS: dict[str, dict[str, Any]] = {}
_SUBMISSIONS: list[dict[str, Any]] = []
_ANCHORS: list[dict[str, Any]] = []
_DB_SYNC_ATTEMPTED = False
_DB_ENABLED = True

_TABLE_WORKORDERS = "mobile_workorders"
_TABLE_SUBMISSIONS = "mobile_submissions"
_TABLE_ANCHORS = "mobile_anchors"

_TRIPROLE_SYNC_EMPTY = {
    "ok": False,
    "action": "",
    "input_proof_id": "",
    "output_proof_id": "",
    "error": "supabase_not_configured_or_unreachable",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _now_text() -> str:
    now = datetime.now()
    return f"{now.month:02d}-{now.day:02d} {now.hour:02d}:{now.minute:02d}"


def _proof_id() -> str:
    seed = f"{datetime.now(UTC).timestamp()}-{uuid4().hex}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8].upper()
    return f"NINST-{digest}"


def _anchor_id() -> str:
    return f"SNP-{uuid4().hex[:10].upper()}"


def _normalize_role(raw: str) -> str:
    text = str(raw or "").strip()
    if text in _ROLE_SET:
        return text

    lookup = {
        "inspect": "检查",
        "inspector": "检查",
        "checker": "检查",
        "record": "记录",
        "recorder": "记录",
        "review": "复核",
        "reviewer": "复核",
        "contractor": "施工单位",
        "builder": "施工单位",
        "supervisor": "监理",
    }
    lowered = text.lower()
    if lowered in lookup:
        return lookup[lowered]
    return "检查"


def _mobile_role_from_dto_role(raw: str) -> str:
    token = str(raw or "").strip().upper()
    mapping = {
        "AI": "检查",
        "SUPERVISOR": "监理",
        "OWNER": "复核",
        "CONTRACTOR": "施工单位",
        "PUBLIC": "记录",
    }
    return mapping.get(token, "检查")


def _decode_uri_text(raw: str) -> str:
    text = unquote(str(raw or "").strip())
    return text


def _normalize_v_uri(raw: str) -> str:
    text = _decode_uri_text(raw)
    if not text:
        return ""
    if text.startswith("v://"):
        return text
    return f"v://cn.dajing/djgs/bridge/{text}"


def _component_code_from_v_uri(v_uri: str) -> str:
    text = str(v_uri or "").strip()
    if not text:
        return ""
    if text.startswith("v://"):
        rows = [item for item in text.split("/") if item]
        if rows:
            return rows[-1]
    return text


def _project_uri_from_v_uri(v_uri: str) -> str:
    text = str(v_uri or "").strip()
    if not text.startswith("v://"):
        return "v://cn.dajing/djgs"
    body = text[4:]
    parts = [item for item in body.split("/") if item]
    if not parts:
        return "v://cn.dajing/djgs"
    if "bridge" in parts:
        idx = parts.index("bridge")
        if idx >= 2:
            return f"v://{'/'.join(parts[:idx])}"
    if len(parts) >= 2:
        return f"v://{parts[0]}/{parts[1]}"
    return f"v://{parts[0]}"


def _segment_uri_from_v_uri(v_uri: str, code: str) -> str:
    text = str(v_uri or "").strip()
    if text.startswith("v://"):
        return text
    if code:
        return f"v://cn.dajing/djgs/bridge/{code}"
    return "v://cn.dajing/djgs/bridge/unknown"


def _normalize_triprole_result(raw: str) -> str:
    text = str(raw or "").strip().lower()
    if text in {"fail", "failed", "false", "ng"}:
        return "FAIL"
    if "不合格" in str(raw or ""):
        return "FAIL"
    return "PASS"


def _guess_triprole_action(step_key: str, step_name: str) -> str:
    token = f"{step_key} {step_name}".strip().lower()
    if "accept" in token or "验收" in token:
        return "gateway.sync"
    if any(key in token for key in ("install", "pour", "rebar", "concrete", "安装", "浇筑", "钢筋", "混凝土")):
        return "measure.record"
    return "quality.check"


def _clone_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": str(row.get("code") or ""),
        "name": str(row.get("name") or ""),
        "v_uri": str(row.get("v_uri") or ""),
        "head_proof_id": str(row.get("head_proof_id") or ""),
        "steps": [{**(step or {})} for step in (row.get("steps") or [])],
    }


def _safe_steps(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item or {}) for item in value if isinstance(item, dict)]


def _safe_client() -> Client | None:
    global _DB_ENABLED
    if not _DB_ENABLED:
        return None
    try:
        return get_supabase_client(error_detail="supabase not configured for mobile")
    except Exception:
        _DB_ENABLED = False
        return None


def _disable_db() -> None:
    global _DB_ENABLED
    _DB_ENABLED = False


def _db_workorder_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "component_code": str(row.get("code") or "").strip(),
        "component_name": str(row.get("name") or "").strip(),
        "v_uri": str(row.get("v_uri") or "").strip(),
        "head_proof_id": str(row.get("head_proof_id") or "").strip(),
        "steps": _safe_steps(row.get("steps")),
        "updated_at": _now_iso(),
    }


def _db_upsert_workorder(sb: Client, row: dict[str, Any]) -> None:
    payload = _db_workorder_payload(row)
    if not payload["component_code"]:
        return
    try:
        sb.table(_TABLE_WORKORDERS).upsert(payload, on_conflict="component_code").execute()
        return
    except Exception:
        # Backward compatibility for databases not migrated with head_proof_id yet.
        legacy_payload = dict(payload)
        legacy_payload.pop("head_proof_id", None)
        sb.table(_TABLE_WORKORDERS).upsert(legacy_payload, on_conflict="component_code").execute()


def _db_list_workorders(sb: Client) -> list[dict[str, Any]]:
    try:
        rows = (
            sb.table(_TABLE_WORKORDERS)
            .select("component_code,component_name,v_uri,head_proof_id,steps")
            .limit(500)
            .execute()
            .data
            or []
        )
    except Exception:
        rows = (
            sb.table(_TABLE_WORKORDERS)
            .select("component_code,component_name,v_uri,steps")
            .limit(500)
            .execute()
            .data
            or []
        )
    out: list[dict[str, Any]] = []
    for item in rows:
        row = dict(item or {})
        code = str(row.get("component_code") or "").strip()
        if not code:
            continue
        out.append(
            {
                "code": code,
                "name": str(row.get("component_name") or "").strip(),
                "v_uri": str(row.get("v_uri") or "").strip(),
                "head_proof_id": str(row.get("head_proof_id") or "").strip(),
                "steps": _safe_steps(row.get("steps")),
            }
        )
    return out


def _pick_latest_unspent_for_segment(
    *,
    engine: ProofUTXOEngine,
    project_uri: str,
    segment_uri: str,
) -> str:
    try:
        rows = engine.get_unspent(
            project_uri=project_uri,
            segment_uri=segment_uri,
            limit=300,
        )
    except Exception:
        rows = []
    if not rows:
        return ""
    sorted_rows = sorted(rows, key=lambda item: str((item or {}).get("created_at") or ""), reverse=True)
    return str((sorted_rows[0] or {}).get("proof_id") or "").strip()


def _ensure_head_proof_id(
    *,
    sb: Client,
    row: dict[str, Any],
    component_code: str,
    v_uri: str,
) -> str:
    engine = ProofUTXOEngine(sb)
    head_proof_id = str(row.get("head_proof_id") or "").strip()
    if head_proof_id:
        existing = engine.get_by_id(head_proof_id)
        if isinstance(existing, dict) and not bool(existing.get("spent")):
            return head_proof_id

    project_uri = _project_uri_from_v_uri(v_uri)
    segment_uri = _segment_uri_from_v_uri(v_uri, component_code)
    latest = _pick_latest_unspent_for_segment(engine=engine, project_uri=project_uri, segment_uri=segment_uri)
    if latest:
        row["head_proof_id"] = latest
        return latest

    seed = hashlib.sha256(f"{project_uri}|{segment_uri}|{component_code}".encode("utf-8")).hexdigest()[:16].upper()
    genesis_id = f"GP-MOBILE-GEN-{seed}"
    state_data = {
        "lifecycle_stage": "INITIAL",
        "status": "INITIAL",
        "component_code": component_code,
        "component_v_uri": v_uri,
        "boq_item_uri": segment_uri,
        "source": "mobile.qcspec",
        "created_by": "mobile-bootstrap",
    }
    created = engine.create(
        proof_id=genesis_id,
        owner_uri=f"v://mobile/component/{component_code}",
        project_uri=project_uri,
        segment_uri=segment_uri,
        proof_type="zero_ledger",
        result="PASS",
        state_data=state_data,
        conditions=[],
        parent_proof_id=None,
        norm_uri="v://norm/mobile/qc-bootstrap/1.0",
        signer_uri="v://executor/system/mobile",
        signer_role="TRIPROLE",
    )
    head = str((created or {}).get("proof_id") or genesis_id).strip() or genesis_id
    row["head_proof_id"] = head
    return head


def _try_execute_triprole_for_mobile(
    *,
    sb: Client,
    row: dict[str, Any],
    component_code: str,
    v_uri: str,
    step_key: str,
    step_name: str,
    executor_uri: str,
    result_text: str,
    form_data: dict[str, Any],
    evidence: list[dict[str, Any]],
    signature: dict[str, Any],
    server_time: str,
    role: str,
) -> dict[str, Any]:
    input_proof_id = _ensure_head_proof_id(
        sb=sb,
        row=row,
        component_code=component_code,
        v_uri=v_uri,
    )
    primary_action = _guess_triprole_action(step_key=step_key, step_name=step_name)
    actions: list[str] = [primary_action]
    if primary_action != "gateway.sync":
        actions.append("gateway.sync")

    payload = {
        "component_code": component_code,
        "component_v_uri": v_uri,
        "step_key": step_key,
        "step_name": step_name,
        "mobile_result": result_text,
        "checked_at": server_time,
        "form_data": dict(form_data or {}),
        "evidence": list(evidence or []),
        "signature": dict(signature or {}),
        "channel": "mobile",
        "role": role,
    }

    last_error = ""
    for action in actions:
        try:
            out = execute_triprole_action(
                sb=sb,
                body={
                    "action": action,
                    "input_proof_id": input_proof_id,
                    "executor_uri": executor_uri,
                    "executor_did": "",
                    "executor_role": "TRIPROLE",
                    "result": _normalize_triprole_result(result_text),
                    "segment_uri": _segment_uri_from_v_uri(v_uri, component_code),
                    "boq_item_uri": _segment_uri_from_v_uri(v_uri, component_code),
                    "payload": payload,
                    "credentials_vc": [],
                    "geo_location": {},
                    "server_timestamp_proof": {"server_time": server_time},
                },
            )
            output_proof_id = str((out or {}).get("output_proof_id") or "").strip()
            if output_proof_id:
                row["head_proof_id"] = output_proof_id
            return {
                "ok": True,
                "action": action,
                "input_proof_id": input_proof_id,
                "output_proof_id": output_proof_id,
                "proof_hash": str((out or {}).get("proof_hash") or "").strip(),
            }
        except Exception as exc:
            last_error = str(exc)

    return {
        "ok": False,
        "action": "",
        "input_proof_id": input_proof_id,
        "output_proof_id": "",
        "error": last_error or "triprole_execution_failed",
    }


def _probe_chain_runtime() -> dict[str, Any]:
    sb = _safe_client()
    if sb is None:
        return {
            "ok": False,
            "mode": "degraded",
            "reason": "supabase_not_configured_or_unreachable",
            "checks": {
                "supabase": False,
                "proof_utxo": False,
                "proof_transaction": False,
                "mobile_workorders": False,
            },
        }

    checks: dict[str, bool] = {
        "supabase": True,
        "proof_utxo": False,
        "proof_transaction": False,
        "mobile_workorders": False,
    }
    reason = "ok"

    try:
        sb.table("proof_utxo").select("proof_id").limit(1).execute()
        checks["proof_utxo"] = True
    except Exception as exc:
        reason = f"proof_utxo_unavailable:{exc}"

    try:
        sb.table("proof_transaction").select("tx_id").limit(1).execute()
        checks["proof_transaction"] = True
    except Exception as exc:
        if reason == "ok":
            reason = f"proof_transaction_unavailable:{exc}"

    try:
        sb.table(_TABLE_WORKORDERS).select("component_code").limit(1).execute()
        checks["mobile_workorders"] = True
    except Exception as exc:
        if reason == "ok":
            reason = f"mobile_workorders_unavailable:{exc}"

    ok = all(bool(value) for value in checks.values())
    return {
        "ok": ok,
        "mode": "ready" if ok else "degraded",
        "reason": "ok" if ok else reason,
        "checks": checks,
    }


def _db_insert_submission(sb: Client, row: dict[str, Any]) -> None:
    form_data = dict(row.get("form_data") or {})
    triprole_sync = row.get("triprole_sync")
    if isinstance(triprole_sync, dict) and triprole_sync:
        form_data["_triprole_sync"] = dict(triprole_sync)
    payload = {
        "submission_id": str(row.get("submission_id") or "").strip(),
        "component_code": str(row.get("component_code") or "").strip(),
        "v_uri": str(row.get("v_uri") or "").strip(),
        "step_key": str(row.get("step_key") or "").strip(),
        "step_name": str(row.get("step_name") or "").strip(),
        "result": str(row.get("result") or "").strip(),
        "proof_id": str(row.get("proof_id") or "").strip(),
        "executor_uri": str(row.get("executor_uri") or "").strip(),
        "device_id": str(row.get("device_id") or "").strip(),
        "timestamp": str(row.get("timestamp") or _now_iso()),
        "form_data": form_data,
        "evidence": list(row.get("evidence") or []),
        "signature": dict(row.get("signature") or {}),
    }
    sb.table(_TABLE_SUBMISSIONS).insert(payload).execute()


def _db_insert_anchor(sb: Client, row: dict[str, Any]) -> None:
    payload = {
        "anchor_id": str(row.get("anchor_id") or "").strip(),
        "trip_id": str(row.get("trip_id") or "").strip(),
        "hash": str(row.get("hash") or "").strip(),
        "location": dict(row.get("location") or {}),
        "timestamp": str(row.get("timestamp") or _now_iso()),
        "anchored_at": str(row.get("anchored_at") or _now_iso()),
    }
    sb.table(_TABLE_ANCHORS).insert(payload).execute()


def _ensure_storage_synced() -> None:
    global _DB_SYNC_ATTEMPTED
    if _DB_SYNC_ATTEMPTED:
        return
    _DB_SYNC_ATTEMPTED = True
    sb = _safe_client()
    if sb is None:
        return
    try:
        rows = _db_list_workorders(sb)
        if rows:
            _WORKORDERS.clear()
            for row in rows:
                code = str(row.get("code") or "").strip()
                if code:
                    _WORKORDERS[code] = _clone_row(row)
            return
        _ensure_seeded()
        for row in _WORKORDERS.values():
            _db_upsert_workorder(sb, row)
    except Exception:
        _disable_db()


def _seed_workorders() -> dict[str, dict[str, Any]]:
    rows = [
        {
            "code": "K12-340-phase4B",
            "name": "K12+340 钻孔灌注桩",
            "v_uri": "v://cn.dajing/djgs/bridge/K12-340-phase4B",
            "steps": [
                {
                    "key": "casing",
                    "name": "护筒埋设",
                    "status": "done",
                    "required_role": "施工单位",
                    "form_name": "桥施6表",
                    "normref_uri": "v://normref.com/qc/template/general-quality-inspection@v1",
                    "done_at": "04-06 09:30",
                    "executor_name": "张三",
                    "proof_id": "NINST-561A7B64",
                },
                {
                    "key": "hole_check",
                    "name": "成孔检查",
                    "status": "current",
                    "required_role": "检查",
                    "form_name": "桥施7表",
                    "normref_uri": "v://normref.com/qc/pile-foundation@v1",
                },
                {
                    "key": "rebar_install",
                    "name": "钢筋安装",
                    "status": "todo",
                    "required_role": "施工单位",
                    "form_name": "桥施11表",
                    "normref_uri": "v://normref.com/qc/rebar-processing@v1",
                },
                {
                    "key": "concrete_pour",
                    "name": "混凝土浇筑",
                    "status": "todo",
                    "required_role": "施工单位",
                    "form_name": "桥施12表",
                    "normref_uri": "v://normref.com/qc/concrete-compressive-test@v1",
                },
                {
                    "key": "acceptance",
                    "name": "验收",
                    "status": "todo",
                    "required_role": "监理",
                    "form_name": "验收检查表",
                    "normref_uri": "v://normref.com/qc/template/general-quality-inspection@v1",
                },
            ],
        },
        {
            "code": "K12-340-4C",
            "name": "K12+340 钻孔灌注桩",
            "v_uri": "v://cn.dajing/djgs/bridge/K12-340-4C",
            "steps": [
                {
                    "key": "casing",
                    "name": "护筒埋设",
                    "status": "done",
                    "required_role": "施工单位",
                    "form_name": "桥施6表",
                    "normref_uri": "v://normref.com/qc/template/general-quality-inspection@v1",
                    "done_at": "04-07 08:40",
                    "executor_name": "李四",
                    "proof_id": "NINST-5BB704CE",
                },
                {
                    "key": "hole_check",
                    "name": "成孔检查",
                    "status": "done",
                    "required_role": "检查",
                    "form_name": "桥施7表",
                    "normref_uri": "v://normref.com/qc/pile-foundation@v1",
                    "done_at": "04-07 09:20",
                    "executor_name": "王工",
                    "proof_id": "NINST-A8E91BCD",
                },
                {
                    "key": "rebar_install",
                    "name": "钢筋安装",
                    "status": "current",
                    "required_role": "施工单位",
                    "form_name": "桥施11表",
                    "normref_uri": "v://normref.com/qc/rebar-processing@v1",
                },
                {
                    "key": "concrete_pour",
                    "name": "混凝土浇筑",
                    "status": "todo",
                    "required_role": "施工单位",
                    "form_name": "桥施12表",
                    "normref_uri": "v://normref.com/qc/concrete-compressive-test@v1",
                },
                {
                    "key": "acceptance",
                    "name": "验收",
                    "status": "todo",
                    "required_role": "监理",
                    "form_name": "验收检查表",
                    "normref_uri": "v://normref.com/qc/template/general-quality-inspection@v1",
                },
            ],
        },
    ]
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = str(row.get("code") or "").strip()
        if code:
            out[code] = _clone_row(row)
    return out


def _ensure_seeded() -> None:
    if _WORKORDERS:
        return
    _WORKORDERS.update(_seed_workorders())


def _ensure_workorder(code: str, v_uri: str = "") -> dict[str, Any]:
    _ensure_seeded()
    key = str(code or "").strip()
    hit = _WORKORDERS.get(key)
    if hit:
        if v_uri and not str(hit.get("v_uri") or "").strip():
            hit["v_uri"] = v_uri
        return hit

    next_v_uri = v_uri or f"v://cn.dajing/djgs/bridge/{key}"
    created = {
        "code": key,
        "name": f"{key} 钻孔灌注桩",
        "v_uri": next_v_uri,
        "head_proof_id": "",
        "steps": [
            {
                "key": "general_check",
                "name": "现场检查",
                "status": "current",
                "required_role": "检查",
                "form_name": "现场检查表",
                "normref_uri": "v://normref.com/qc/template/general-quality-inspection@v1",
            }
        ],
    }
    _WORKORDERS[key] = created
    return created


def _pick_current_step(steps: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in steps:
        if str(row.get("status") or "") == "current":
            return row
    for row in steps:
        if str(row.get("status") or "") == "todo":
            return row
    return steps[0] if steps else None


class MobileSubmitBody(BaseModel):
    v_uri: str = ""
    component_code: str = ""
    step_key: str = ""
    step_name: str = ""
    result: str = "合格"
    form_data: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    signature: dict[str, Any] = Field(default_factory=dict)
    executor_uri: str = ""
    timestamp: str = ""
    device_id: str = ""


class MobileAnchorBody(BaseModel):
    photo: str = ""
    hash: str = ""
    trip_id: str = ""
    location: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""


class MobileSignatureBody(BaseModel):
    provider: str = ""
    component_code: str = ""
    step_name: str = ""
    role: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("/me-role")
async def get_mobile_me_role(request: Request):
    token = str(request.headers.get("authorization") or "").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    else:
        token = ""

    if not token:
        return {"ok": True, "role": "检查", "source": "guest"}

    sb = _safe_client()
    if sb is None:
        return {"ok": True, "role": "检查", "source": "fallback"}

    try:
        identity = require_auth_user(token=token, sb=sb)
    except Exception:
        return {"ok": True, "role": "检查", "source": "fallback"}

    dto_role = str(identity.get("dto_role") or "").strip()
    return {
        "ok": True,
        "source": "auth",
        "dto_role": dto_role,
        "role": _mobile_role_from_dto_role(dto_role),
        "user_name": str(identity.get("name") or "").strip(),
        "user_id": str(identity.get("id") or "").strip(),
    }


@router.get("/executor/{executor_id}/workorder")
async def get_executor_workorders(executor_id: str):
    role = _normalize_role(_decode_uri_text(executor_id).split("/")[-1])
    with _DATA_LOCK:
        _ensure_storage_synced()
        _ensure_seeded()
        rows: list[dict[str, Any]] = []
        for workorder in _WORKORDERS.values():
            steps = [step for step in (workorder.get("steps") or []) if isinstance(step, dict)]
            current = _pick_current_step(steps)
            if not current:
                continue
            if str(current.get("required_role") or "") != role:
                continue
            rows.append(
                {
                    "component_code": workorder.get("code"),
                    "component_name": workorder.get("name"),
                    "v_uri": workorder.get("v_uri"),
                    "current_step": {
                        "key": current.get("key"),
                        "name": current.get("name"),
                        "required_role": current.get("required_role"),
                        "form_name": current.get("form_name"),
                    },
                }
            )
    return {
        "ok": True,
        "executor_id": _decode_uri_text(executor_id),
        "role": role,
        "pending_count": len(rows),
        "workorders": rows,
        "server_time": _now_iso(),
    }


@router.get("/component/{v_uri:path}/current-step")
async def get_component_current_step(v_uri: str):
    next_v_uri = _normalize_v_uri(v_uri)
    if not next_v_uri:
        raise HTTPException(400, "v_uri is required")
    code = _component_code_from_v_uri(next_v_uri)
    if not code:
        raise HTTPException(400, "invalid_v_uri")
    with _DATA_LOCK:
        _ensure_storage_synced()
        row = _ensure_workorder(code=code, v_uri=next_v_uri)
        sb = _safe_client()
        if sb is not None:
            try:
                _db_upsert_workorder(sb, row)
            except Exception:
                _disable_db()
        return {
            "ok": True,
            "component_code": row.get("code"),
            "component_name": row.get("name"),
            "v_uri": row.get("v_uri"),
            "steps": [dict(step or {}) for step in (row.get("steps") or [])],
            "server_time": _now_iso(),
        }


@router.get("/chain-status")
async def get_mobile_chain_status():
    payload = _probe_chain_runtime()
    payload["server_time"] = _now_iso()
    return payload


@router.post("/trips/submit-mobile")
async def submit_mobile_trip(body: MobileSubmitBody, request: Request):
    code = str(body.component_code or "").strip()
    v_uri = _normalize_v_uri(body.v_uri or code)
    if not code and v_uri:
        code = _component_code_from_v_uri(v_uri)
    if not code:
        raise HTTPException(400, "component_code is required")

    server_time = _now_iso()
    device_id = str(request.headers.get("x-device-id") or "").strip() or str(request.headers.get("user-agent") or "")
    step_key = str(body.step_key or "").strip()
    role = _normalize_role(str(body.executor_uri or "").split("/")[-1])
    executor_uri = f"v://mobile/executor/{role}"
    proof_id = _proof_id()
    triprole_sync = dict(_TRIPROLE_SYNC_EMPTY)

    with _DATA_LOCK:
        _ensure_storage_synced()
        row = _ensure_workorder(code=code, v_uri=v_uri)
        steps = [dict(step or {}) for step in (row.get("steps") or [])]
        target_index = -1
        if step_key:
            for index, step in enumerate(steps):
                if str(step.get("key") or "") == step_key:
                    target_index = index
                    break
        if target_index < 0:
            current = _pick_current_step(steps)
            target_index = steps.index(current) if current in steps else -1
        if target_index < 0:
            raise HTTPException(400, "step_not_found")

        step = steps[target_index]
        sb = _safe_client()
        if sb is not None:
            try:
                triprole_sync = _try_execute_triprole_for_mobile(
                    sb=sb,
                    row=row,
                    component_code=code,
                    v_uri=v_uri,
                    step_key=str(step.get("key") or body.step_key or "").strip(),
                    step_name=str(step.get("name") or body.step_name or "").strip(),
                    executor_uri=executor_uri,
                    result_text=str(body.result or ""),
                    form_data=dict(body.form_data or {}),
                    evidence=list(body.evidence or []),
                    signature=dict(body.signature or {}),
                    server_time=server_time,
                    role=role,
                )
                output_proof_id = str(triprole_sync.get("output_proof_id") or "").strip()
                if output_proof_id:
                    proof_id = output_proof_id
            except Exception as exc:
                triprole_sync = {
                    "ok": False,
                    "action": "",
                    "input_proof_id": "",
                    "output_proof_id": "",
                    "error": str(exc) or "triprole_execution_failed",
                }
        else:
            triprole_sync = dict(_TRIPROLE_SYNC_EMPTY)
        step["status"] = "done"
        step["done_at"] = _now_text()
        step["executor_name"] = role
        step["proof_id"] = proof_id
        steps[target_index] = step

        for next_index in range(target_index + 1, len(steps)):
            if str(steps[next_index].get("status") or "") == "todo":
                steps[next_index]["status"] = "current"
                break

        row["steps"] = steps
        row["v_uri"] = v_uri

        next_step = _pick_current_step(steps)
        submission = {
            "submission_id": f"MSUB-{uuid4().hex[:10].upper()}",
            "component_code": code,
            "v_uri": v_uri,
            "step_key": step.get("key"),
            "step_name": step.get("name") or body.step_name,
            "result": str(body.result or "合格"),
            "proof_id": proof_id,
            "executor_uri": executor_uri,
            "device_id": device_id,
            "timestamp": server_time,
            "form_data": dict(body.form_data or {}),
            "evidence": list(body.evidence or []),
            "signature": dict(body.signature or {}),
            "triprole_sync": dict(triprole_sync or {}),
        }
        _SUBMISSIONS.append(submission)
        if sb is not None:
            try:
                _db_upsert_workorder(sb, row)
                _db_insert_submission(sb, submission)
            except Exception:
                _disable_db()

    return {
        "ok": True,
        "proof_id": proof_id,
        "executor_uri": executor_uri,
        "timestamp": server_time,
        "device_id": device_id,
        "component_code": code,
        "step_name": submission["step_name"],
        "triprole_sync": triprole_sync,
        "next_step": (next_step or {}).get("name") or "等待施工员操作",
        "message": "提交成功",
    }


@router.get("/qrcode/{v_uri:path}")
async def get_component_qrcode(v_uri: str):
    content = _normalize_v_uri(v_uri)
    if not content:
        raise HTTPException(400, "v_uri is required")
    image = qrcode.make(content)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


@router.post("/snappeg/anchor")
async def anchor_mobile_photo(body: MobileAnchorBody):
    raw_photo = str(body.photo or "").strip()
    raw_hash = str(body.hash or "").strip().lower()
    if not raw_photo:
        raise HTTPException(400, "photo is required")
    if not raw_hash:
        raise HTTPException(400, "hash is required")

    try:
        photo_bytes = base64.b64decode(raw_photo, validate=True)
    except Exception as exc:  # pragma: no cover - defensive path
        raise HTTPException(400, f"invalid_photo_base64: {exc}") from exc

    calc_hash = hashlib.sha256(photo_bytes).hexdigest()
    if calc_hash != raw_hash:
        raise HTTPException(400, "photo_hash_mismatch")

    row = {
        "anchor_id": _anchor_id(),
        "trip_id": str(body.trip_id or "").strip(),
        "hash": calc_hash,
        "location": dict(body.location or {}),
        "timestamp": str(body.timestamp or "").strip() or _now_iso(),
        "anchored_at": _now_iso(),
    }
    with _DATA_LOCK:
        _ANCHORS.append(row)
        sb = _safe_client()
        if sb is not None:
            try:
                _db_insert_anchor(sb, row)
            except Exception:
                _disable_db()

    return {
        "ok": True,
        "anchor_id": row["anchor_id"],
        "trip_id": row["trip_id"],
        "hash": row["hash"],
        "anchored_at": row["anchored_at"],
    }


@router.post("/signature/confirm")
async def confirm_mobile_signature(body: MobileSignatureBody):
    provider = str(body.provider or "").strip().lower()
    if provider not in {"signpeg", "ca"}:
        raise HTTPException(400, "provider must be signpeg or ca")

    role = _normalize_role(body.role)
    signed_at = _now_iso()
    digest_source = {
        "provider": provider,
        "component_code": str(body.component_code or "").strip(),
        "step_name": str(body.step_name or "").strip(),
        "role": role,
        "payload": dict(body.payload or {}),
        "signed_at": signed_at,
    }
    digest = hashlib.sha256(
        json.dumps(digest_source, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    token = f"{provider}://server-signed-{digest[:24]}"
    return {
        "ok": True,
        "provider": provider,
        "role": role,
        "signed_at": signed_at,
        "token": token,
        "signature": token,
    }

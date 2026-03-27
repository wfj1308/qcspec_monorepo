"""
Public verify routes (no auth).
services/api/routers/verify.py
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import hashlib
import io
import json
import os
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from supabase import Client, create_client

from archive_service import create_dsp_package
from specir_engine import (
    derive_spec_uri as specir_derive_spec_uri,
    evaluate_measurements as specir_evaluate_measurements,
    normalize_operator as specir_normalize_operator,
    normalize_spec_uri as specir_normalize_spec_uri,
    resolve_spec_rule as specir_resolve_spec_rule,
    result_cn as specir_result_cn,
    spec_excerpt as specir_spec_excerpt,
    threshold_text as specir_threshold_text,
)

from .proof_utxo_engine import ProofUTXOEngine
from workers.gitpeg_anchor_worker import GitPegAnchorWorker

public_router = APIRouter()


@lru_cache(maxsize=1)
def _supabase_client_cached(url: str, key: str) -> Client:
    return create_client(url, key)


def _get_supabase() -> Client:
    url = str(os.getenv("SUPABASE_URL") or "").strip()
    key = str(
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    ).strip()
    if not url or not key:
        raise HTTPException(500, "Supabase not configured")
    return _supabase_client_cached(url, key)


def _verify_base_url() -> str:
    base = str(os.getenv("QCSPEC_VERIFY_BASE_URL") or "https://verify.qcspec.com").strip()
    return base.rstrip("/")


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    return str(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        text = str(value).strip()
        if not text:
            return None
        m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None


def _parse_limit(value: Any) -> float | None:
    text = _to_text(value).strip()
    if not text:
        return None
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return abs(float(m.group(0)))
    except Exception:
        return None


def _format_num(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _display_time(value: Any) -> str:
    """Force second-level timestamp format: YYYY-MM-DD HH:mm:ss"""
    text = _to_text(value).strip()
    if not text:
        return "-"
    normalized = text
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(normalized)
        return dt.replace(tzinfo=None, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    cleaned = text.replace("T", " ").strip()
    cleaned = re.sub(r"\.\d+", "", cleaned)
    cleaned = re.sub(r"(Z|[+-]\d{2}:?\d{2})$", "", cleaned).strip()
    sec_match = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", cleaned)
    if sec_match:
        return sec_match.group(1).replace("  ", " ")
    min_match = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})$", cleaned)
    if min_match:
        return f"{min_match.group(1).replace('  ', ' ')}:00"
    return cleaned


def _parse_dt_for_sort(value: Any) -> datetime:
    text = _to_text(value).strip()
    if not text:
        return datetime.min
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        return datetime.fromisoformat(normalized).replace(tzinfo=None)
    except Exception:
        return datetime.min


def _result_cn(value: Any) -> str:
    return specir_result_cn(value)


def _status_token(value: Any) -> str:
    token = _to_text(value).strip().upper()
    if token in {"PASS", "SUCCESS", "OK"}:
        return "pass"
    if token in {"FAIL", "REJECTED", "ERROR"}:
        return "fail"
    return "pending"


def _extract_sign_info(row: dict[str, Any]) -> dict[str, str]:
    signed_by = row.get("signed_by") if isinstance(row.get("signed_by"), list) else []
    first = signed_by[0] if signed_by and isinstance(signed_by[0], dict) else {}

    name = ""
    for key in ("executor_name", "name", "display_name", "signer_name"):
        v = _to_text(first.get(key)).strip()
        if v:
            name = v
            break

    executor_uri = _to_text(first.get("executor_uri") or row.get("owner_uri") or "-")
    if not name:
        name = executor_uri.rstrip("/").split("/")[-1] if executor_uri else "-"
        if not name:
            name = "-"

    role = _to_text(first.get("role") or "AI").strip().upper() or "AI"
    ordosign_hash = _to_text(first.get("ordosign_hash") or row.get("ordosign_hash") or "-")
    signed_at = _display_time(first.get("ts") or row.get("created_at"))

    return {
        "name": name,
        "executor_uri": executor_uri,
        "role": role,
        "ordosign_hash": ordosign_hash,
        "signed_at": signed_at,
    }


def _stake_from_row(row: dict[str, Any]) -> str:
    sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
    stake = _to_text(sd.get("stake") or sd.get("location") or "").strip()
    if stake:
        return stake
    segment_uri = _to_text(row.get("segment_uri") or sd.get("segment_uri") or "").strip().rstrip("/")
    if segment_uri and "/" in segment_uri:
        return segment_uri.split("/")[-1]
    return "-"


def _coerce_values(state_data: dict[str, Any]) -> list[float]:
    values: list[float] = []
    vals = state_data.get("values") if isinstance(state_data.get("values"), list) else []
    for v in vals:
        fv = _to_float(v)
        if fv is not None:
            values.append(fv)
    if not values:
        fv = _to_float(state_data.get("value"))
        if fv is not None:
            values.append(fv)
    return values


def _normalize_operator(raw_op: Any) -> str:
    return specir_normalize_operator(raw_op)


def _resolve_rule(state_data: dict[str, Any]) -> tuple[str, float | None, float | None]:
    op = _normalize_operator(
        state_data.get("standard_op")
        or state_data.get("standard_operator")
        or state_data.get("operator")
        or state_data.get("comparator")
        or ""
    )
    standard = _to_float(state_data.get("standard_value"))
    if standard is None:
        standard = _to_float(state_data.get("standard"))
    if standard is None:
        standard = _to_float(state_data.get("design"))

    tolerance = _to_float(state_data.get("standard_tolerance"))
    if tolerance is None:
        tolerance = _parse_limit(state_data.get("limit"))

    token = f"{_to_text(state_data.get('type') or '')} {_to_text(state_data.get('type_name') or '')}".lower()
    if not op:
        if tolerance is not None and standard is not None:
            op = "±"
        elif any(k in token for k in ("compaction", "density", "压实度", "压实")):
            op = ">="
        else:
            op = "<="

    return op, standard, tolerance


def _eval_rule_result(values: list[float], operator: str, standard: float | None, tolerance: float | None, fallback: str) -> str:
    evaluated = specir_evaluate_measurements(
        values=values,
        operator=operator,
        threshold=standard,
        tolerance=tolerance,
        fallback_result=fallback,
    )
    return _to_text(evaluated.get("result") or fallback).upper()


def _rule_threshold_text(operator: str, standard: float | None, tolerance: float | None) -> str:
    return specir_threshold_text(operator, standard, tolerance)


def _values_text(values: list[float], unit: str) -> str:
    if not values:
        return "-"
    arr = [_format_num(v) for v in values]
    val = "/".join(arr)
    u = _to_text(unit).strip()
    return f"{val} {u}".strip()


def _normalize_spec_uri(raw: Any) -> str:
    return specir_normalize_spec_uri(raw)


def _derive_spec_uri(row: dict[str, Any]) -> str:
    sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
    return specir_derive_spec_uri(
        sd,
        row_norm_uri=row.get("norm_uri"),
        fallback_norm_ref=sd.get("norm_ref"),
    )


def _spec_excerpt(spec_uri: str) -> str:
    return specir_spec_excerpt(spec_uri)


def _hash_payload_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "proof_id": _to_text(row.get("proof_id") or ""),
        "owner_uri": _to_text(row.get("owner_uri") or ""),
        "project_uri": _to_text(row.get("project_uri") or ""),
        "project_id": row.get("project_id"),
        "segment_uri": row.get("segment_uri"),
        "proof_type": _to_text(row.get("proof_type") or "inspection").lower(),
        "result": _to_text(row.get("result") or "PENDING").upper(),
        "state_data": row.get("state_data") if isinstance(row.get("state_data"), dict) else {},
        "conditions": row.get("conditions") if isinstance(row.get("conditions"), list) else [],
        "parent_proof_id": row.get("parent_proof_id"),
        "norm_uri": row.get("norm_uri"),
    }


def _hash_json(payload: dict[str, Any]) -> tuple[str, str]:
    source = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return digest, source


def get_proof_ancestry(
    engine: ProofUTXOEngine,
    proof_id: str,
    *,
    max_depth: int = 128,
    _seen: set[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Recursively trace parent_proof_id upward until initial_import or root.
    Returns ancestry ordered from root -> current proof.
    """
    current_id = _to_text(proof_id).strip()
    if not current_id or max_depth <= 0:
        return []

    seen = _seen or set()
    if current_id in seen:
        return []
    seen.add(current_id)

    row = engine.get_by_id(current_id)
    if not isinstance(row, dict):
        return []

    proof_type = _to_text(row.get("proof_type") or "").strip().lower()
    parent_id = _to_text(row.get("parent_proof_id") or "").strip()

    if proof_type == "initial_import" or not parent_id:
        return [row]

    parent_chain = get_proof_ancestry(engine, parent_id, max_depth=max_depth - 1, _seen=seen)
    return parent_chain + [row]


def get_proof_descendants(
    engine: ProofUTXOEngine,
    proof_id: str,
    *,
    max_depth: int = 8,
    max_nodes: int = 256,
) -> list[dict[str, Any]]:
    """
    Breadth-first descendants traversal (children -> deeper descendants).
    Ordered by created_at ascending.
    """
    root_id = _to_text(proof_id).strip()
    if not root_id:
        return []

    queue: list[tuple[str, int]] = [(root_id, 0)]
    seen: set[str] = {root_id}
    out: list[dict[str, Any]] = []

    while queue and len(out) < max_nodes:
        node_id, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        try:
            children = (
                engine.sb.table("proof_utxo")
                .select("*")
                .eq("parent_proof_id", node_id)
                .order("created_at", desc=False)
                .limit(200)
                .execute()
                .data
                or []
            )
        except Exception:
            children = []

        for child in children:
            cid = _to_text((child or {}).get("proof_id") or "").strip()
            if not cid or cid in seen:
                continue
            seen.add(cid)
            out.append(child)
            queue.append((cid, depth + 1))
            if len(out) >= max_nodes:
                break

    out.sort(key=lambda row: _parse_dt_for_sort(row.get("created_at")))
    return out


def _remediation_info(
    *,
    root_proof_id: str,
    descendants_enriched: list[dict[str, Any]],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    latest_pass = None
    for item in descendants_enriched:
        token = _to_text(item.get("computed_result") or "").upper()
        proof_type = _to_text(item.get("proof_type") or "").lower()
        is_remedial = (
            "rect" in proof_type
            or "repair" in proof_type
            or "reinspect" in proof_type
            or "整改" in _to_text(item.get("test_name"))
            or "复检" in _to_text(item.get("test_name"))
            or proof_type in {"inspection", "proof"}
        )
        if not is_remedial:
            continue
        rec = {
            "proof_id": item.get("proof_id"),
            "proof_type": item.get("proof_type"),
            "result": token or "PENDING",
            "result_cn": _result_cn(token or "PENDING"),
            "time": item.get("created_at"),
            "executor": item.get("executor_name") or "-",
            "description": f"{item.get('test_name') or item.get('proof_type') or '整改记录'} · {item.get('measured') or '-'}",
            "proof_hash": item.get("proof_hash") or "",
            "hash_valid": bool(item.get("proof_hash_valid")),
            "parent": item.get("parent_proof_id") or "-",
        }
        records.append(rec)
        if token == "PASS":
            latest_pass = rec

    issue_seed = hashlib.sha256(f"{root_proof_id}|remediation".encode("utf-8")).hexdigest()[:8].upper()
    issue_id = f"RC-{issue_seed}"
    return {
        "issue_id": issue_id,
        "has_remediation": bool(records),
        "latest_pass_proof_id": (latest_pass or {}).get("proof_id") or "",
        "records": records,
    }


def _enriched_row(row: dict[str, Any], *, sb: Client | None = None) -> dict[str, Any]:
    sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
    meta = sd.get("meta") if isinstance(sd.get("meta"), dict) else {}
    sign = _extract_sign_info(row)
    test_type = _to_text(sd.get("type") or sd.get("test_type") or row.get("proof_type") or "proof")
    test_name = _to_text(sd.get("type_name") or sd.get("test_name") or test_type)
    stake = _to_text(sd.get("stake") or sd.get("location") or "-") or "-"
    values = _coerce_values(sd)
    spec_uri = _derive_spec_uri(row)
    component_type = _to_text(sd.get("component_type") or sd.get("structure_type") or sd.get("part_type"))
    spec_rule = specir_resolve_spec_rule(
        spec_uri=spec_uri,
        metric=test_name,
        test_type=test_type,
        test_name=test_name,
        context={"component_type": component_type, "stake": stake},
        sb=sb,
    )

    op, standard, tolerance = _resolve_rule(sd)
    if _to_text(spec_rule.get("operator")).strip():
        op = _to_text(spec_rule.get("operator"))
    if spec_rule.get("threshold") is not None:
        standard = _to_float(spec_rule.get("threshold"))
    if spec_rule.get("tolerance") is not None:
        tolerance = _to_float(spec_rule.get("tolerance"))

    unit = _to_text(sd.get("unit") or spec_rule.get("unit") or "").strip()
    evaluated = specir_evaluate_measurements(
        values=values,
        operator=op,
        threshold=standard,
        tolerance=tolerance,
        fallback_result=_to_text(row.get("result") or "PENDING"),
    )
    computed = _to_text(evaluated.get("result") or row.get("result") or "PENDING").upper()
    deviation_pct = evaluated.get("deviation_percent")

    threshold = specir_threshold_text(op, standard, tolerance, unit)
    measured = _values_text(values, unit)
    effective_spec_uri = _to_text(spec_rule.get("effective_spec_uri") or spec_uri)
    spec_snapshot = _to_text(
        meta.get("spec_snapshot")
        or meta.get("spec_excerpt")
        or sd.get("spec_snapshot")
        or sd.get("spec_excerpt")
    ).strip()
    spec_excerpt = spec_snapshot or specir_spec_excerpt(effective_spec_uri, fallback_excerpt=spec_rule.get("excerpt"))

    provided_hash = _to_text(row.get("proof_hash") or "")
    hash_payload = _hash_payload_from_row(row)
    recomputed_hash, _ = _hash_json(hash_payload)
    hash_valid = bool(provided_hash and provided_hash.lower() == recomputed_hash.lower())

    return {
        "proof_id": _to_text(row.get("proof_id") or ""),
        "proof_hash": provided_hash,
        "proof_hash_recomputed": recomputed_hash,
        "proof_hash_valid": hash_valid,
        "proof_type": _to_text(row.get("proof_type") or ""),
        "parent_proof_id": _to_text(row.get("parent_proof_id") or ""),
        "created_at": _display_time(row.get("created_at")),
        "created_at_raw": _to_text(row.get("created_at") or ""),
        "executor_name": sign["name"],
        "executor_uri": sign["executor_uri"],
        "executor_role": sign["role"],
        "ordosign_hash": sign["ordosign_hash"],
        "signed_at": sign["signed_at"],
        "spec_uri": effective_spec_uri or spec_uri,
        "spec_excerpt": spec_excerpt,
        "spec_version": _to_text(spec_rule.get("version") or ""),
        "spec_code": _to_text(spec_rule.get("code") or ""),
        "spec_source": _to_text(spec_rule.get("source") or ""),
        "rule_source_uri": _to_text(spec_rule.get("effective_spec_uri") or effective_spec_uri or spec_uri),
        "operator": op,
        "threshold": threshold,
        "threshold_num": standard,
        "tolerance_num": tolerance,
        "measured": measured,
        "measured_values": values,
        "computed_result": computed,
        "computed_result_cn": _result_cn(computed),
        "deviation_percent": deviation_pct,
        "stored_result": _to_text(row.get("result") or "").upper(),
        "test_type": test_type,
        "test_name": test_name,
        "stake": stake,
        "component_type": component_type or "-",
        "meta": {
            "spec_snapshot": spec_snapshot,
            "spec_uri": _to_text(meta.get("spec_uri") or effective_spec_uri or spec_uri),
            "spec_version": _to_text(meta.get("spec_version") or spec_rule.get("version") or ""),
            "captured_at": _display_time(meta.get("captured_at") or row.get("created_at")),
        },
        "evidence_hashes": [
            _to_text(x).strip().lower()
            for x in (sd.get("evidence_hashes") if isinstance(sd.get("evidence_hashes"), list) else [])
            if _to_text(x).strip()
        ],
    }


def _build_qcgate(ancestry_enriched: list[dict[str, Any]], stake: str) -> dict[str, Any]:
    rules: list[dict[str, Any]] = []
    for item in ancestry_enriched:
        rule_id = f"QCRule::{item['test_type']}::{item['operator']}::{item['threshold']}"
        rules.append(
            {
                "rule_id": rule_id,
                "spec_uri": item["spec_uri"],
                "spec_excerpt": item["spec_excerpt"],
                "spec_version": item.get("spec_version"),
                "rule_source_uri": item.get("rule_source_uri"),
                "operator": item["operator"],
                "threshold": item["threshold"],
                "measured": item["measured"],
                "result": item["computed_result"],
                "result_cn": item.get("computed_result_cn"),
                "deviation_percent": item.get("deviation_percent"),
                "source_proof_id": item["proof_id"],
                "proof_hash": item.get("proof_hash"),
                "recomputed_hash": item.get("proof_hash_recomputed"),
                "hash_valid": item.get("proof_hash_valid"),
                "executed_at": item["created_at"],
            }
        )

    gate_status = "PASS"
    if any(_to_text(r.get("result") or "").upper() == "FAIL" for r in rules):
        gate_status = "FAIL"
    elif not rules:
        gate_status = "PENDING"

    gate_id = f"QCGate::{stake or 'K50+200'}"
    return {
        "gate_id": gate_id,
        "stake": stake,
        "status": gate_status,
        "pass_policy": "all_pass",
        "rule_count": len(rules),
        "all_hash_valid": all(bool(r.get("hash_valid")) for r in rules) if rules else True,
        "rules": rules,
    }


def _build_timeline(ancestry_enriched: list[dict[str, Any]], qcgate: dict[str, Any]) -> list[dict[str, Any]]:
    if not ancestry_enriched:
        return []
    first = ancestry_enriched[0]
    latest = ancestry_enriched[-1]

    spec_uri = first.get("spec_uri") or latest.get("spec_uri") or ""
    spec_excerpt = first.get("spec_excerpt") or latest.get("spec_excerpt") or ""
    gate_status = _to_text(qcgate.get("status") or "PENDING").upper()

    return [
        {
            "step": 1,
            "type": "SpecIR",
            "title": "规范基准锚定",
            "description": spec_uri or "未绑定规范地址",
            "time": first.get("created_at"),
            "executor": "SpecIR",
            "status": "pass" if spec_uri else "pending",
            "spec_uri": spec_uri,
            "spec_excerpt": spec_excerpt,
        },
        {
            "step": 2,
            "type": "QCRule",
            "title": "AI 规则翻译",
            "description": (
                f"由 SpecIR 翻译为可执行规则：{latest.get('operator') or '-'} "
                f"{latest.get('threshold') or '-'}，实测 {latest.get('measured') or '-'}"
            ),
            "time": latest.get("created_at"),
            "executor": "QCRule Engine",
            "status": "fail" if gate_status == "FAIL" else ("pass" if gate_status == "PASS" else "pending"),
            "spec_uri": spec_uri,
            "spec_excerpt": spec_excerpt,
            "operator": latest.get("operator"),
            "threshold": latest.get("threshold"),
            "rule_source_uri": latest.get("rule_source_uri"),
        },
        {
            "step": 3,
            "type": "TripRole",
            "title": "现场实测录入",
            "description": f"{latest.get('executor_name') or '-'} 录入 {latest.get('measured') or '-'}",
            "time": latest.get("created_at"),
            "executor": latest.get("executor_name") or "-",
            "status": "pass" if _to_text(latest.get("computed_result")).upper() == "PASS" else "fail",
            "spec_uri": spec_uri,
            "spec_excerpt": spec_excerpt,
        },
        {
            "step": 4,
            "type": "Proof",
            "title": "系统判定与签名",
            "description": (
                f"系统自动判定：{_result_cn(latest.get('computed_result'))}；"
                f"OrdoSign: {latest.get('ordosign_hash') or '-'}"
            ),
            "time": latest.get("signed_at") or latest.get("created_at"),
            "executor": latest.get("executor_name") or "Proof UTXO",
            "status": "pass" if _to_text(latest.get("computed_result")).upper() == "PASS" else "fail",
            "proof_id": latest.get("proof_id"),
            "spec_uri": spec_uri,
            "spec_excerpt": spec_excerpt,
        },
    ]


def _build_chain(ancestry_enriched: list[dict[str, Any]], current_proof_id: str) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    for item in ancestry_enriched:
        result = _to_text(item.get("computed_result") or "PENDING").upper()
        chain.append(
            {
                "type": "Proof",
                "proof_type": item.get("proof_type"),
                "label": item.get("test_name") or item.get("proof_type") or "Proof 节点",
                "status": _status_token(result),
                "result": result,
                "time": item.get("created_at"),
                "actor": f"{item.get('executor_name')} [{item.get('executor_role')}]",
                "proof": item.get("proof_id"),
                "proof_id": item.get("proof_id"),
                "parent": item.get("parent_proof_id") or "-",
                "current": _to_text(item.get("proof_id")) == _to_text(current_proof_id),
                "executor": item.get("executor_uri"),
                "executor_name": item.get("executor_name"),
                "spec_uri": item.get("spec_uri"),
                "operator": item.get("operator"),
                "threshold": item.get("threshold"),
                "proof_hash": item.get("proof_hash"),
                "hash_valid": item.get("proof_hash_valid"),
            }
        )
    return chain


def _build_audit_rows(ancestry_enriched: list[dict[str, Any]], qcgate: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in ancestry_enriched:
        rows.append(
            {
                "proof_id": item.get("proof_id"),
                "type": "Proof",
                "proof_type": item.get("proof_type"),
                "result": _to_text(item.get("computed_result") or "PENDING").upper(),
                "parent": item.get("parent_proof_id") or "-",
                "time": item.get("created_at"),
                "executor": item.get("executor_uri"),
                "executor_name": item.get("executor_name"),
                "spec_uri": item.get("spec_uri"),
                "operator": item.get("operator"),
                "threshold": item.get("threshold"),
                "proof_hash": item.get("proof_hash"),
                "recomputed_hash": item.get("proof_hash_recomputed"),
                "hash_valid": item.get("proof_hash_valid"),
                "_raw_created_at": item.get("created_at_raw"),
            }
        )
    gate_id = _to_text(qcgate.get("gate_id") or "QCGate")
    gate_rules = qcgate.get("rules") if isinstance(qcgate.get("rules"), list) else []
    for rule in gate_rules:
        if not isinstance(rule, dict):
            continue
        rows.append(
            {
                "proof_id": rule.get("source_proof_id") or "-",
                "type": "QCRule",
                "proof_type": rule.get("rule_id") or "QCRule",
                "result": _to_text(rule.get("result") or "PENDING").upper(),
                "parent": gate_id,
                "time": rule.get("executed_at") or "-",
                "executor": "QCRule Engine",
                "executor_name": "QCRule Engine",
                "spec_uri": rule.get("spec_uri"),
                "operator": rule.get("operator"),
                "threshold": rule.get("threshold"),
                "proof_hash": rule.get("proof_hash"),
                "recomputed_hash": rule.get("recomputed_hash"),
                "hash_valid": rule.get("hash_valid"),
                "_raw_created_at": rule.get("executed_at"),
            }
        )
    rows.sort(key=lambda item: _parse_dt_for_sort(item.get("_raw_created_at")), reverse=True)
    for i, row in enumerate(rows, start=1):
        row["index"] = i
        row.pop("_raw_created_at", None)
    return rows


def _build_context(row: dict[str, Any], stake: str, executor_uri: str) -> dict[str, str]:
    sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
    project_uri = _to_text(row.get("project_uri") or sd.get("project_uri") or "").strip()

    resolved_stake = _to_text(stake).strip()
    if not resolved_stake or resolved_stake == "-":
        resolved_stake = "K50+200"

    segment_uri = _to_text(row.get("segment_uri") or sd.get("segment_uri") or "").strip()
    if not segment_uri:
        if project_uri:
            segment_uri = f"{project_uri.rstrip('/')}/segment/{resolved_stake}"
        else:
            segment_uri = f"v://cn/segment/{resolved_stake}"

    return {
        "project_uri": project_uri,
        "segment_uri": segment_uri,
        "stake": resolved_stake,
        "executor_uri": _to_text(executor_uri or "-") or "-",
        "contract_uri": _to_text(sd.get("contract_uri") or ""),
        "design_uri": _to_text(sd.get("design_uri") or ""),
    }


def _build_gitpeg_status(gitpeg_anchor: str) -> dict[str, Any]:
    anchor = _to_text(gitpeg_anchor).strip()
    if not anchor:
        return {
            "anchored": False,
            "anchor_ref": "",
            "block_height": None,
            "message": "已在本地存证，等待全局锚定",
        }

    block_height = None
    merkle_root = ""
    m = re.search(r"(?:height|block(?:_height)?)[=: ](\d+)", anchor, flags=re.IGNORECASE)
    if m:
        try:
            block_height = int(m.group(1))
        except Exception:
            block_height = None
    merkle_match = re.search(r"(?:merkle|mr)[=: ]([a-fA-F0-9]{8,64})", anchor, flags=re.IGNORECASE)
    if merkle_match:
        merkle_root = _to_text(merkle_match.group(1)).lower()

    msg = f"已锚定：{anchor}"
    if block_height is not None:
        msg = f"已锚定，区块高度 {block_height}"

    return {
        "anchored": True,
        "anchor_ref": anchor,
        "block_height": block_height,
        "merkle_root": merkle_root,
        "message": msg,
    }


def _extract_evidence_hash(raw: dict[str, Any]) -> str:
    for key in ("evidence_hash", "sha256", "file_sha256", "hash"):
        text = _to_text(raw.get(key) if isinstance(raw, dict) else "").strip().lower()
        if text:
            return text
    return ""


def _extract_media_type(raw: dict[str, Any]) -> str:
    content_type = _to_text(raw.get("content_type") if isinstance(raw, dict) else "").strip().lower()
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    file_name = _to_text(raw.get("file_name") if isinstance(raw, dict) else "").strip().lower()
    if file_name.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic")):
        return "image"
    if file_name.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")):
        return "video"
    return "file"


def _collect_evidence(
    *,
    sb: Client,
    latest_row: dict[str, Any],
    chain_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    inspection_ids: set[str] = set()
    expected_hashes: set[str] = set()
    expected_proofs: set[str] = set()
    inline_items: list[dict[str, Any]] = []

    for row in chain_rows:
        if not isinstance(row, dict):
            continue
        sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
        insp_id = _to_text(sd.get("inspection_id")).strip()
        if insp_id:
            inspection_ids.add(insp_id)
        for h in sd.get("evidence_hashes") if isinstance(sd.get("evidence_hashes"), list) else []:
            text = _to_text(h).strip().lower()
            if text:
                expected_hashes.add(text)
        for p in sd.get("evidence_proof_ids") if isinstance(sd.get("evidence_proof_ids"), list) else []:
            text = _to_text(p).strip()
            if text:
                expected_proofs.add(text)

        inline = sd.get("evidence") if isinstance(sd.get("evidence"), list) else []
        for item in inline:
            if not isinstance(item, dict):
                continue
            ehash = _extract_evidence_hash(item)
            pid = _to_text(item.get("proof_id")).strip()
            if ehash:
                expected_hashes.add(ehash)
            if pid:
                expected_proofs.add(pid)
            inline_items.append(
                {
                    "id": _to_text(item.get("id") or ""),
                    "file_name": _to_text(item.get("file_name") or item.get("name") or "-"),
                    "url": _to_text(item.get("url") or item.get("storage_url") or ""),
                    "media_type": _extract_media_type(item),
                    "evidence_hash": ehash,
                    "proof_id": pid,
                    "proof_hash": _to_text(item.get("proof_hash") or "").lower(),
                    "size": item.get("size") or item.get("file_size"),
                    "time": _display_time(item.get("taken_at") or item.get("created_at") or ""),
                    "source": "proof_state",
                }
            )

    latest_sd = latest_row.get("state_data") if isinstance(latest_row.get("state_data"), dict) else {}
    latest_insp = _to_text(latest_sd.get("inspection_id")).strip()
    if latest_insp:
        inspection_ids.add(latest_insp)

    db_items: list[dict[str, Any]] = []
    for inspection_id in inspection_ids:
        try:
            rows = (
                sb.table("photos")
                .select("*")
                .eq("inspection_id", inspection_id)
                .order("created_at", desc=True)
                .limit(100)
                .execute()
                .data
                or []
            )
        except Exception:
            rows = []
        for photo in rows:
            if not isinstance(photo, dict):
                continue
            ehash = _extract_evidence_hash(photo)
            proof_id = _to_text(photo.get("proof_id")).strip()
            proof_hash = _to_text(photo.get("proof_hash")).strip().lower()
            if ehash:
                expected_hashes.add(ehash)
            if proof_id:
                expected_proofs.add(proof_id)
            url = _to_text(photo.get("storage_url") or "")
            if not url:
                path = _to_text(photo.get("storage_path") or "")
                if path:
                    url = path
            db_items.append(
                {
                    "id": _to_text(photo.get("id") or ""),
                    "file_name": _to_text(photo.get("file_name") or "-"),
                    "url": url,
                    "media_type": _extract_media_type(photo),
                    "evidence_hash": ehash,
                    "proof_id": proof_id,
                    "proof_hash": proof_hash,
                    "size": photo.get("file_size"),
                    "time": _display_time(photo.get("taken_at") or photo.get("created_at")),
                    "source": "photos_table",
                }
            )

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in db_items + inline_items:
        key = "|".join(
            [
                _to_text(item.get("id") or ""),
                _to_text(item.get("proof_id") or ""),
                _to_text(item.get("evidence_hash") or ""),
                _to_text(item.get("url") or ""),
            ]
        )
        if key in seen:
            continue
        seen.add(key)
        eh = _to_text(item.get("evidence_hash") or "").lower()
        pid = _to_text(item.get("proof_id") or "")
        ph = _to_text(item.get("proof_hash") or "").lower()
        hash_matched = bool(
            (eh and eh in expected_hashes)
            or (pid and pid in expected_proofs)
            or (ph and ph in expected_hashes)
        )
        merged.append(
            {
                **item,
                "hash_matched": hash_matched,
                "hash_match_text": "文件哈希已匹配" if hash_matched else "文件哈希待核验",
            }
        )
    return merged


def _mock_signer_cert(executor_uri: str) -> dict[str, str]:
    seed = hashlib.sha256(_to_text(executor_uri).encode("utf-8")).hexdigest()
    pub = f"MOCK-ED25519-{seed[:64]}"
    pem = (
        "-----BEGIN PUBLIC KEY-----\n"
        f"{pub}\n"
        "-----END PUBLIC KEY-----\n"
    )
    return {"algorithm": "ed25519-mock", "public_key": pub, "public_key_pem": pem}


@public_router.get("/spec/resolve")
async def resolve_spec_rule_public(
    spec_uri: str,
    metric: str = "",
    component_type: str = "",
):
    """
    Public SpecIR resolve endpoint.
    GET /api/verify/spec/resolve?spec_uri=v://norm/...
    GET /api/v1/verify/spec/resolve?spec_uri=v://norm/...
    """
    sb = _get_supabase()
    resolved = specir_resolve_spec_rule(
        spec_uri=spec_uri,
        metric=metric,
        test_type=metric,
        test_name=metric,
        context={"component_type": component_type},
        sb=sb,
    )
    return {
        "ok": True,
        "input_spec_uri": specir_normalize_spec_uri(spec_uri),
        "resolved": resolved,
        "threshold_text": specir_threshold_text(
            resolved.get("operator"),
            _to_float(resolved.get("threshold")),
            _to_float(resolved.get("tolerance")),
            resolved.get("unit"),
        ),
    }


@public_router.post("/anchor/mock-run")
async def run_mock_anchor_once():
    """
    Manual trigger for mock GitPeg anchor handshake.
    Useful for demo/testing immediate backfill.
    """
    worker = GitPegAnchorWorker()
    result = worker.anchor_once()
    return {"ok": True, "worker_enabled": worker.enabled, "result": result}


@public_router.get("/{proof_id}")
async def get_public_verify_detail(proof_id: str):
    """
    Public read-only verify endpoint.
    GET /api/verify/{proof_id}
    GET /api/v1/verify/{proof_id}
    """
    proof_id = _to_text(proof_id).strip()
    if not proof_id:
        raise HTTPException(400, "proof_id is required")

    sb = _get_supabase()
    engine = ProofUTXOEngine(sb)
    row = engine.get_by_id(proof_id)
    if not isinstance(row, dict):
        raise HTTPException(404, "proof_utxo not found")

    ancestry = get_proof_ancestry(engine, proof_id)
    if not ancestry:
        ancestry = [row]

    ancestry_enriched = [_enriched_row(x, sb=sb) for x in ancestry]
    latest = ancestry[-1]
    latest_enriched = ancestry_enriched[-1]
    sd = latest.get("state_data") if isinstance(latest.get("state_data"), dict) else {}

    project_name = "-"
    project_id = _to_text(latest.get("project_id") or "").strip()
    if project_id:
        try:
            proj_res = (
                sb.table("projects")
                .select("id,name")
                .eq("id", project_id)
                .limit(1)
                .execute()
            )
            if proj_res.data:
                project_name = _to_text((proj_res.data[0] or {}).get("name") or "-")
        except Exception:
            project_name = "-"

    context = _build_context(latest, _stake_from_row(latest), latest_enriched.get("executor_uri") or "-")
    qcgate = _build_qcgate(ancestry_enriched, context["stake"])

    computed_result = _to_text(latest_enriched.get("computed_result") or "PENDING").upper()
    result_cn = _result_cn(computed_result)
    verify_url = f"{_verify_base_url()}/v/{_to_text(latest.get('proof_id') or '')}"

    hash_payload = _hash_payload_from_row(latest)
    recomputed_hash, hash_source_json = _hash_json(hash_payload)
    proof_hash = _to_text(latest.get("proof_hash") or "")
    hash_match = bool(proof_hash and recomputed_hash.lower() == proof_hash.lower())

    gitpeg_anchor = _to_text(latest.get("gitpeg_anchor") or "")
    gitpeg_status = _build_gitpeg_status(gitpeg_anchor)

    spec_uri = latest_enriched.get("spec_uri") or ""
    if not spec_uri:
        for x in ancestry_enriched:
            if _to_text(x.get("spec_uri")).strip():
                spec_uri = _to_text(x.get("spec_uri"))
                break

    descendants: list[dict[str, Any]] = []
    descendants_enriched: list[dict[str, Any]] = []
    remediation = {
        "issue_id": "",
        "has_remediation": False,
        "latest_pass_proof_id": "",
        "records": [],
    }
    if computed_result == "FAIL":
        descendants = get_proof_descendants(engine, proof_id)
        descendants_enriched = [_enriched_row(x, sb=sb) for x in descendants if isinstance(x, dict)]
        remediation = _remediation_info(root_proof_id=proof_id, descendants_enriched=descendants_enriched)

    timeline = _build_timeline(ancestry_enriched, qcgate)
    if remediation.get("has_remediation"):
        timeline.append(
            {
                "step": len(timeline) + 1,
                "type": "Remediation",
                "title": f"已关联整改单 [{remediation.get('issue_id')}]",
                "description": (
                    f"整改后代记录 {len(remediation.get('records') or [])} 条；"
                    f"最近复检合格 Proof: {remediation.get('latest_pass_proof_id') or '-'}"
                ),
                "time": ((remediation.get("records") or [{}])[-1] or {}).get("time") or latest_enriched.get("created_at"),
                "executor": "RectifyFlow",
                "status": "pass" if remediation.get("latest_pass_proof_id") else "pending",
                "spec_uri": spec_uri,
                "spec_excerpt": latest_enriched.get("spec_excerpt") or "",
            }
        )
    chain_rows = ancestry_enriched + descendants_enriched
    chain = _build_chain(chain_rows, proof_id)
    audit_rows = _build_audit_rows(chain_rows, qcgate)
    evidence_items = _collect_evidence(sb=sb, latest_row=latest, chain_rows=ancestry + descendants)
    spec_snapshot = _to_text((latest_enriched.get("meta") or {}).get("spec_snapshot") or latest_enriched.get("spec_excerpt") or "").strip()

    return {
        "ok": True,
        "verified": hash_match,
        "proof_id": _to_text(latest.get("proof_id") or ""),
        "verify_url": verify_url,
        "context": context,
        "hash_verification": {
            "algorithm": "sha256",
            "provided_hash": proof_hash,
            "recomputed_hash": recomputed_hash,
            "matches": hash_match,
            "source_json": hash_source_json,
        },
        "hash_payload": hash_payload,
        "summary": {
            "project_name": project_name,
            "project_uri": context["project_uri"],
            "segment_uri": context["segment_uri"],
            "stake": context["stake"],
            "test_name": latest_enriched.get("test_name") or "检测项",
            "value": latest_enriched.get("measured") or "-",
            "standard": latest_enriched.get("threshold") or "-",
            "result": computed_result,
            "result_cn": result_cn,
            "deviation_percent": latest_enriched.get("deviation_percent"),
            "created_at": latest_enriched.get("created_at") or "-",
            "spec_uri": spec_uri,
            "spec_version": latest_enriched.get("spec_version") or "",
            "rule_source_uri": latest_enriched.get("rule_source_uri") or "",
            "spec_snapshot": spec_snapshot,
            "action_item_id": remediation.get("issue_id") if computed_result == "FAIL" else "",
        },
        "sovereignty": {
            "proof_id": _to_text(latest.get("proof_id") or ""),
            "proof_hash": proof_hash,
            "v_uri": _to_text(sd.get("v_uri") or context["project_uri"] or ""),
            "gitpeg_anchor": gitpeg_anchor,
            "gitpeg_status": gitpeg_status,
            "ordosign_hash": latest_enriched.get("ordosign_hash") or "-",
            "executor_uri": latest_enriched.get("executor_uri") or "-",
            "signed_by": latest_enriched.get("executor_name") or "-",
            "signed_role": latest_enriched.get("executor_role") or "AI",
            "signed_at": latest_enriched.get("signed_at") or "-",
        },
        "exec": {
            "test_type": latest_enriched.get("test_name") or "检测项",
            "stake": context["stake"],
            "value": latest_enriched.get("measured") or "-",
            "standard": latest_enriched.get("threshold") or "-",
            "norm": spec_uri or "-",
            "operator": latest_enriched.get("operator") or "-",
            "threshold": latest_enriched.get("threshold") or "-",
        },
        "person": {
            "name": latest_enriched.get("executor_name") or "-",
            "uri": latest_enriched.get("executor_uri") or "-",
            "role": latest_enriched.get("executor_role") or "AI",
            "time": latest_enriched.get("signed_at") or "-",
            "sign": latest_enriched.get("ordosign_hash") or "-",
        },
        "qcgate": qcgate,
        "remediation": remediation,
        "timeline": timeline,
        "chain": chain,
        "evidence": evidence_items,
        "audit": {
            "depth": max(len(ancestry) - 1, 0) + len(descendants_enriched),
            "rows": audit_rows,
        },
    }


@public_router.get("/{proof_id}/dsp")
async def download_dsp_package(proof_id: str):
    """
    Data Sovereignty Package (DSP):
    - report.pdf
    - proof_chain.json
    - verify_offline.html
    - signer_certificate.pem
    """
    proof_id = _to_text(proof_id).strip()
    if not proof_id:
        raise HTTPException(400, "proof_id is required")

    detail = await get_public_verify_detail(proof_id)
    sb = _get_supabase()
    engine = ProofUTXOEngine(sb)

    ancestry = get_proof_ancestry(engine, proof_id)
    descendants = get_proof_descendants(engine, proof_id, max_depth=12, max_nodes=512)
    raw_chain = ancestry + descendants

    chain_fingerprints: list[dict[str, Any]] = []
    for row in raw_chain:
        if not isinstance(row, dict):
            continue
        payload = _hash_payload_from_row(row)
        digest, source = _hash_json(payload)
        chain_fingerprints.append(
            {
                "proof_id": _to_text(row.get("proof_id") or ""),
                "proof_hash": _to_text(row.get("proof_hash") or ""),
                "recomputed_hash": digest,
                "hash_valid": _to_text(row.get("proof_hash") or "").lower() == digest.lower(),
                "proof_type": _to_text(row.get("proof_type") or ""),
                "parent_proof_id": _to_text(row.get("parent_proof_id") or ""),
                "created_at": _display_time(row.get("created_at")),
                "source_fingerprint": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            }
        )

    person = detail.get("person") if isinstance(detail.get("person"), dict) else {}
    cert = _mock_signer_cert(_to_text(person.get("uri") or "v://executor/system"))

    dsp_bytes = create_dsp_package(
        proof_id=proof_id,
        verify_detail=detail,
        chain_fingerprints=chain_fingerprints,
        signer_certificate=cert,
    )
    filename = f"DSP-{proof_id}.zip"
    return StreamingResponse(
        io.BytesIO(dsp_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

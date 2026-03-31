"""
BOQ-centric sovereign history + reconciliation engine.

Implements:
- get_item_sovereign_history(subitem_code)
- run_boq_audit_engine(project_uri)
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import HTTPException

from services.api.triprole_engine import _compute_docfinal_risk_audit


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        text = _to_text(value).strip().replace(",", "")
        if not text:
            return None
        try:
            return float(text)
        except Exception:
            return None


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _row_fingerprint(row: dict[str, Any]) -> dict[str, Any]:
    sd = _as_dict(row.get("state_data"))
    v_uri_refs = [
        _to_text(row.get("project_uri") or "").strip(),
        _to_text(row.get("segment_uri") or "").strip(),
        _to_text(row.get("norm_uri") or "").strip(),
        _to_text(sd.get("v_uri") or "").strip(),
        _to_text(sd.get("boq_item_uri") or sd.get("item_uri") or "").strip(),
        _to_text(sd.get("norm_uri") or sd.get("spec_uri") or "").strip(),
    ]
    v_uri_refs = [uri for uri in v_uri_refs if uri.startswith("v://")]

    payload = {
        "proof_id": _to_text(row.get("proof_id") or ""),
        "proof_hash": _to_text(row.get("proof_hash") or ""),
        "parent_proof_id": _to_text(row.get("parent_proof_id") or ""),
        "project_uri": _to_text(row.get("project_uri") or ""),
        "segment_uri": _to_text(row.get("segment_uri") or ""),
        "proof_type": _to_text(row.get("proof_type") or ""),
        "result": _to_text(row.get("result") or ""),
        "state_data": sd if isinstance(sd, dict) else {},
        "norm_uri": _to_text(row.get("norm_uri") or ""),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    row_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "proof_id": payload["proof_id"],
        "proof_hash": payload["proof_hash"],
        "row_hash": row_hash,
        "parent_proof_id": payload["parent_proof_id"],
        "proof_type": payload["proof_type"],
        "result": payload["result"],
        "created_at": _to_text(row.get("created_at") or ""),
        "segment_uri": payload["segment_uri"],
        "norm_uri": payload["norm_uri"],
        "v_uri_refs": sorted(set(v_uri_refs)),
        "geo_location": _as_dict(sd.get("geo_location")),
        "server_timestamp_proof": _as_dict(sd.get("server_timestamp_proof")),
        "spatiotemporal_anchor_hash": _to_text(sd.get("spatiotemporal_anchor_hash") or "").strip(),
    }


def _chain_root_hash(fingerprints: list[dict[str, Any]]) -> str:
    canonical = json.dumps(fingerprints, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _item_code_from_boq_uri(boq_item_uri: str) -> str:
    uri = _to_text(boq_item_uri).strip().rstrip("/")
    if not uri:
        return ""
    return uri.split("/")[-1]


def _extract_boq_item_uri(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    for key in ("boq_item_uri", "item_uri", "boq_uri"):
        candidate = _to_text(sd.get(key) or "").strip()
        if candidate.startswith("v://"):
            return candidate
    segment_uri = _to_text(row.get("segment_uri") or "").strip()
    if "/boq/" in segment_uri:
        return segment_uri
    return ""


def _extract_item_code(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    code = _to_text(sd.get("item_no") or "").strip()
    if code:
        return code
    return _item_code_from_boq_uri(_extract_boq_item_uri(row))


def _extract_settled_quantity(row: dict[str, Any]) -> float:
    sd = _as_dict(row.get("state_data"))
    settlement = _as_dict(sd.get("settlement"))
    for candidate in (
        settlement.get("settled_quantity"),
        settlement.get("quantity"),
        settlement.get("confirmed_quantity"),
        settlement.get("approved_quantity"),
        sd.get("settled_quantity"),
    ):
        v = _to_float(candidate)
        if v is not None:
            return float(v)
    return 0.0


def _extract_variation_delta(row: dict[str, Any]) -> float:
    sd = _as_dict(row.get("state_data"))
    delta = _to_float(_as_dict(sd.get("delta_utxo")).get("delta_amount"))
    if delta is None:
        delta = _to_float(_as_dict(sd.get("variation")).get("delta_amount"))
    if delta is None:
        delta = _to_float(_as_dict(sd.get("ledger")).get("last_delta_amount"))
    return float(delta or 0.0)


def _is_initial_row(row: dict[str, Any]) -> bool:
    sd = _as_dict(row.get("state_data"))
    lifecycle = _to_text(sd.get("lifecycle_stage") or "").strip().upper()
    status = _to_text(sd.get("status") or "").strip().upper()
    ptype = _to_text(row.get("proof_type") or "").strip().lower()
    if lifecycle == "INITIAL" or status == "INITIAL":
        return True
    return ptype == "zero_ledger"


def _is_variation_row(row: dict[str, Any]) -> bool:
    sd = _as_dict(row.get("state_data"))
    action = _to_text(sd.get("trip_action") or "").strip().lower()
    lifecycle = _to_text(sd.get("lifecycle_stage") or "").strip().upper()
    return action == "variation.delta.apply" or lifecycle == "VARIATION" or bool(_as_dict(sd.get("delta_utxo")))


def _is_settlement_row(row: dict[str, Any]) -> bool:
    sd = _as_dict(row.get("state_data"))
    ptype = _to_text(row.get("proof_type") or "").strip().lower()
    action = _to_text(sd.get("trip_action") or "").strip().lower()
    lifecycle = _to_text(sd.get("lifecycle_stage") or "").strip().upper()
    return ptype == "payment" or action == "settlement.confirm" or lifecycle == "SETTLEMENT"


def _is_document_row(row: dict[str, Any]) -> bool:
    ptype = _to_text(row.get("proof_type") or "").strip().lower()
    if ptype in {"document", "photo", "erpnext_receipt"}:
        return True
    sd = _as_dict(row.get("state_data"))
    return bool(_to_text(sd.get("doc_type") or "").strip())


def _load_project_rows(*, sb: Any, project_uri: str, max_rows: int = 50000) -> list[dict[str, Any]]:
    try:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("project_uri", project_uri)
            .order("created_at", desc=False)
            .limit(max_rows)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(502, f"failed to load proof_utxo: {exc}") from exc
    return [row for row in rows if isinstance(row, dict)]


def _source_utxo_refs(row: dict[str, Any]) -> list[str]:
    sd = _as_dict(row.get("state_data"))
    refs: list[str] = []
    direct = _to_text(sd.get("source_utxo_id") or "").strip()
    if direct:
        refs.append(direct)
    refs.extend([_to_text(x).strip() for x in _as_list(sd.get("source_utxo_ids")) if _to_text(x).strip()])
    refs.extend([_to_text(x).strip() for x in _as_list(sd.get("compensates")) if _to_text(x).strip()])
    return sorted(set(refs))


def get_item_sovereign_history(
    *,
    sb: Any,
    project_uri: str,
    subitem_code: str,
    max_rows: int = 50000,
) -> dict[str, Any]:
    code = _to_text(subitem_code).strip()
    if not code:
        raise HTTPException(400, "subitem_code is required")

    rows = _load_project_rows(sb=sb, project_uri=project_uri, max_rows=max_rows)
    target = [
        row
        for row in rows
        if _extract_item_code(row) == code or _item_code_from_boq_uri(_extract_boq_item_uri(row)) == code
    ]
    if not target:
        raise HTTPException(404, f"no BOQ proof found for subitem_code={code}")

    target.sort(key=lambda x: _to_text(x.get("created_at") or ""))
    initial = next((row for row in target if _is_initial_row(row)), target[0])
    root_id = _to_text(initial.get("proof_id") or "").strip()
    root_uri = _extract_boq_item_uri(initial)
    if not root_id:
        raise HTTPException(500, "invalid root utxo for subitem")
    initial_sd = _as_dict(initial.get("state_data"))
    design_qty = _to_float(initial_sd.get("design_quantity"))
    approved_qty = _to_float(initial_sd.get("approved_quantity"))
    contract_qty = _to_float(initial_sd.get("contract_quantity"))
    unit_price = _to_float(initial_sd.get("unit_price"))
    design_total = _to_float(initial_sd.get("design_total"))
    if design_total is None and unit_price is not None and design_qty is not None:
        design_total = float(unit_price) * float(design_qty)
    contract_total = _to_float(initial_sd.get("contract_total"))
    if contract_total is None and unit_price is not None and contract_qty is not None:
        contract_total = float(unit_price) * float(contract_qty)
    ledger_snapshot = {
        "item_no": _extract_item_code(initial),
        "item_name": _to_text(initial_sd.get("item_name") or "").strip(),
        "unit": _to_text(initial_sd.get("unit") or "").strip(),
        "design_quantity": design_qty,
        "approved_quantity": approved_qty,
        "contract_quantity": contract_qty,
        "unit_price": unit_price,
        "design_total": design_total,
        "contract_total": contract_total,
        "boq_item_uri": root_uri,
    }

    children_by_parent: dict[str, list[dict[str, Any]]] = {}
    row_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        pid = _to_text(row.get("proof_id") or "").strip()
        if pid:
            row_by_id[pid] = row
        parent_id = _to_text(row.get("parent_proof_id") or "").strip()
        if parent_id:
            children_by_parent.setdefault(parent_id, []).append(row)

    queue = [root_id]
    visited: set[str] = set()
    chain_rows: list[dict[str, Any]] = []
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        node = row_by_id.get(current)
        if node:
            chain_rows.append(node)
        for child in children_by_parent.get(current, []):
            child_id = _to_text(child.get("proof_id") or "").strip()
            if child_id and child_id not in visited:
                queue.append(child_id)

    # Include linked document proofs that reference source_utxo_id / source_utxo_ids.
    linked_docs = []
    for row in rows:
        pid = _to_text(row.get("proof_id") or "").strip()
        if not pid or pid in visited:
            continue
        refs = _source_utxo_refs(row)
        if not refs:
            continue
        if any(ref in visited for ref in refs):
            linked_docs.append(row)
            visited.add(pid)

    combined = chain_rows + linked_docs
    by_id: dict[str, dict[str, Any]] = {}
    for row in combined:
        pid = _to_text(row.get("proof_id") or "").strip()
        if pid and pid not in by_id:
            by_id[pid] = row
    ordered = sorted(by_id.values(), key=lambda x: _to_text(x.get("created_at") or ""))

    depth_by_id: dict[str, int] = {root_id: 0}
    for row in ordered:
        pid = _to_text(row.get("proof_id") or "").strip()
        parent = _to_text(row.get("parent_proof_id") or "").strip()
        if not pid:
            continue
        if parent and parent in depth_by_id:
            depth_by_id[pid] = depth_by_id[parent] + 1
        else:
            depth_by_id.setdefault(pid, 0 if pid == root_id else 1)

    timeline: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    variation_count = 0
    settlement_count = 0
    fail_count = 0

    chain_sorted = sorted(chain_rows, key=lambda x: _to_text(x.get("created_at") or ""))
    chain_fingerprints = [_row_fingerprint(row) for row in chain_sorted if isinstance(row, dict)]
    total_proof_hash = _chain_root_hash(chain_fingerprints) if chain_fingerprints else ""
    risk_audit: dict[str, Any] = {}
    if chain_sorted:
        try:
            risk_audit = _compute_docfinal_risk_audit(
                sb=sb,
                project_uri=project_uri,
                boq_item_uri=root_uri,
                chain_rows=chain_sorted,
            )
            if total_proof_hash:
                risk_audit["total_proof_hash"] = total_proof_hash
        except Exception:
            risk_audit = {}

    for row in ordered:
        sd = _as_dict(row.get("state_data"))
        pid = _to_text(row.get("proof_id") or "").strip()
        ptype = _to_text(row.get("proof_type") or "").strip().lower()
        result = _to_text(row.get("result") or "").strip().upper()
        if result == "FAIL":
            fail_count += 1
        if _is_variation_row(row):
            variation_count += 1
        if _is_settlement_row(row):
            settlement_count += 1

        entry = {
            "proof_id": pid,
            "parent_proof_id": _to_text(row.get("parent_proof_id") or "").strip(),
            "proof_hash": _to_text(row.get("proof_hash") or "").strip(),
            "proof_type": ptype,
            "result": result,
            "created_at": _to_text(row.get("created_at") or "").strip(),
            "depth": int(depth_by_id.get(pid, 0)),
            "trip_action": _to_text(sd.get("trip_action") or "").strip(),
            "lifecycle_stage": _to_text(sd.get("lifecycle_stage") or "").strip(),
            "status": _to_text(sd.get("status") or "").strip(),
            "item_no": _extract_item_code(row),
            "boq_item_uri": _extract_boq_item_uri(row),
            "source_utxo_ids": _source_utxo_refs(row),
            "spent": bool(row.get("spent")),
            "summary": _to_text(sd.get("summary") or sd.get("item_name") or "").strip(),
        }
        timeline.append(entry)

        if _is_document_row(row):
            report_url = _to_text(sd.get("report_url") or "").strip()
            documents.append(
                {
                    "proof_id": pid,
                    "proof_hash": _to_text(row.get("proof_hash") or "").strip(),
                    "created_at": _to_text(row.get("created_at") or "").strip(),
                    "doc_type": _to_text(sd.get("doc_type") or "").strip(),
                    "file_name": _to_text(sd.get("file_name") or "").strip(),
                    "mime_type": _to_text(sd.get("mime_type") or "").strip(),
                    "storage_url": _to_text(sd.get("storage_url") or report_url or "").strip(),
                    "report_url": report_url,
                    "doc_status": _to_text(sd.get("status") or "").strip(),
                    "trip_action": _to_text(sd.get("trip_action") or "").strip(),
                    "lifecycle_stage": _to_text(sd.get("lifecycle_stage") or "").strip(),
                    "node_uri": _to_text(sd.get("node_uri") or "").strip(),
                    "source_utxo_id": _to_text(sd.get("source_utxo_id") or "").strip(),
                    "tags": _as_list(sd.get("tags")),
                }
            )

    return {
        "ok": True,
        "project_uri": project_uri,
        "subitem_code": code,
        "boq_item_uri": root_uri,
        "root_utxo_id": root_id,
        "root_proof_hash": _to_text(initial.get("proof_hash") or "").strip(),
        "total_proof_hash": total_proof_hash,
        "risk_audit": risk_audit,
        "ledger_snapshot": ledger_snapshot,
        "totals": {
            "proof_count": len(timeline),
            "document_count": len(documents),
            "variation_count": variation_count,
            "settlement_count": settlement_count,
            "fail_count": fail_count,
        },
        "timeline": timeline,
        "documents": documents,
        "chain_proof_ids": [_to_text(row.get("proof_id") or "").strip() for row in ordered if _to_text(row.get("proof_id") or "").strip()],
    }


def run_boq_audit_engine(
    *,
    sb: Any,
    project_uri: str,
    subitem_code: str = "",
    max_rows: int = 50000,
    limit_items: int = 2000,
) -> dict[str, Any]:
    normalized_code = _to_text(subitem_code).strip()
    rows = _load_project_rows(sb=sb, project_uri=project_uri, max_rows=max_rows)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        code = _extract_item_code(row)
        if not code:
            continue
        if normalized_code and code != normalized_code:
            continue
        grouped.setdefault(code, []).append(row)

    audits: list[dict[str, Any]] = []
    illegal_attempts: list[dict[str, Any]] = []

    for code, bucket in grouped.items():
        ordered = sorted(bucket, key=lambda x: _to_text(x.get("created_at") or ""))
        initial_row = next((r for r in ordered if _is_initial_row(r)), ordered[0] if ordered else {})
        initial_sd = _as_dict(_as_dict(initial_row).get("state_data"))
        design_qty = float(_to_float(initial_sd.get("design_quantity")) or 0.0)
        approved_qty = _to_float(initial_sd.get("approved_quantity"))
        baseline_qty = float(approved_qty if approved_qty is not None else design_qty)

        variation_total = 0.0
        settled_total = 0.0
        first_uri = _extract_boq_item_uri(initial_row)
        item_name = _to_text(initial_sd.get("item_name") or "").strip()
        unit = _to_text(initial_sd.get("unit") or "").strip()
        variation_count = 0
        settlement_count = 0

        for row in ordered:
            sd = _as_dict(row.get("state_data"))
            result = _to_text(row.get("result") or "").strip().upper()
            if _is_variation_row(row):
                variation_total += _extract_variation_delta(row)
                variation_count += 1
            if _is_settlement_row(row) and result == "PASS":
                settled_total += _extract_settled_quantity(row)
                settlement_count += 1
            if result == "FAIL":
                action = _to_text(sd.get("trip_action") or "").strip().lower()
                ptype = _to_text(row.get("proof_type") or "").strip().lower()
                if action in {"settlement.confirm", "measure.record", "variation.record"} or ptype in {"payment", "inspection"}:
                    illegal_attempts.append(
                        {
                            "subitem_code": code,
                            "boq_item_uri": _extract_boq_item_uri(row) or first_uri,
                            "proof_id": _to_text(row.get("proof_id") or "").strip(),
                            "created_at": _to_text(row.get("created_at") or "").strip(),
                            "reason": _to_text(sd.get("error") or sd.get("warning") or sd.get("fail_reason") or "failed_attempt").strip(),
                            "action": action or ptype,
                        }
                    )

        consumable = baseline_qty + variation_total
        deviation = consumable - settled_total
        oversettled = settled_total - consumable
        if oversettled > 1e-9:
            illegal_attempts.append(
                {
                    "subitem_code": code,
                    "boq_item_uri": first_uri,
                    "proof_id": "",
                    "created_at": "",
                    "reason": "oversettlement_detected",
                    "action": "audit_rule",
                    "oversettled_quantity": round(oversettled, 6),
                }
            )

        audits.append(
            {
                "subitem_code": code,
                "boq_item_uri": first_uri,
                "item_name": item_name,
                "unit": unit,
                "design_quantity": round(design_qty, 6),
                "approved_quantity": round(float(approved_qty), 6) if approved_qty is not None else None,
                "baseline_quantity": round(baseline_qty, 6),
                "variation_quantity": round(variation_total, 6),
                "settled_quantity": round(settled_total, 6),
                "consumable_quantity": round(consumable, 6),
                "deviation_quantity": round(deviation, 6),
                "variation_count": variation_count,
                "settlement_count": settlement_count,
                "illegal_attempt_count": sum(1 for x in illegal_attempts if _to_text(x.get("subitem_code") or "").strip() == code),
                "status": "balanced" if abs(deviation) <= 1e-9 else ("oversettled" if deviation < 0 else "remaining"),
            }
        )

    audits = sorted(audits, key=lambda x: _to_text(x.get("subitem_code") or ""))[: max(1, min(limit_items, 10000))]
    illegal_attempts = sorted(illegal_attempts, key=lambda x: (_to_text(x.get("subitem_code") or ""), _to_text(x.get("created_at") or "")))
    summary = {
        "item_count": len(audits),
        "design_total": round(sum(float(x.get("design_quantity") or 0.0) for x in audits), 6),
        "baseline_total": round(sum(float(x.get("baseline_quantity") or 0.0) for x in audits), 6),
        "variation_total": round(sum(float(x.get("variation_quantity") or 0.0) for x in audits), 6),
        "settled_total": round(sum(float(x.get("settled_quantity") or 0.0) for x in audits), 6),
        "deviation_total": round(sum(float(x.get("deviation_quantity") or 0.0) for x in audits), 6),
        "illegal_attempt_count": len(illegal_attempts),
    }
    return {
        "ok": True,
        "project_uri": project_uri,
        "subitem_code": normalized_code,
        "summary": summary,
        "items": audits,
        "illegal_attempts": illegal_attempts[:5000],
    }

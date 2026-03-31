"""
Evidence center helpers.
services/api/evidence_center_service.py
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from supabase import Client

from services.api.docpeg_proof_chain_service import get_proof_chain
from services.api.verify_evidence_service import build_evidence_items


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


def _display_time(value: Any) -> str:
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


def get_all_evidence_for_item(
    *,
    sb: Client,
    boq_item_uri: str,
) -> dict[str, Any]:
    """
    Recursively collect evidence for a BOQ item.
    Includes inline evidence hashes + SnapPeg photos linked by inspection_id.
    """
    item_uri = _to_text(boq_item_uri).strip()
    if not item_uri:
        return {"ok": False, "error": "boq_item_uri is required", "evidence": []}

    chain_rows = get_proof_chain(item_uri, sb)
    if not chain_rows:
        return {"ok": False, "error": "no proof chain", "evidence": []}

    chain_rows.sort(key=lambda row: _to_text((row or {}).get("created_at") or ""))
    latest_row = chain_rows[-1] if chain_rows else {}

    evidence_items = build_evidence_items(
        sb=sb,
        latest_row=_as_dict(latest_row),
        chain_rows=chain_rows,
        display_time=_display_time,
    )
    scan_entries: list[dict[str, Any]] = []
    meshpeg_entries: list[dict[str, Any]] = []
    formula_entries: list[dict[str, Any]] = []
    gateway_entries: list[dict[str, Any]] = []
    for row in chain_rows:
        if not isinstance(row, dict):
            continue
        proof_type = _to_text(row.get("proof_type") or "").strip().lower()
        sd = _as_dict(row.get("state_data"))
        trip_action = _to_text(sd.get("trip_action") or "").strip().lower()
        if proof_type == "scan_entry" or trip_action == "scan.entry":
            scan = _as_dict(sd.get("scan_entry"))
            geo = _as_dict(sd.get("geo_location") or scan.get("geo_location"))
            created_at = _display_time(
                scan.get("scan_entry_at")
                or sd.get("trip_executed_at")
                or row.get("created_at")
            )
            token_hash = _to_text(scan.get("token_hash") or sd.get("scan_entry_hash") or "").strip()
            token_present = scan.get("token_present")
            scan_entries.append(
                {
                    "item_uri": item_uri,
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                    "created_at": created_at,
                    "status": _to_text(scan.get("status") or row.get("result") or sd.get("status") or "").strip().lower(),
                    "token": (
                        "submitted"
                        if token_present or token_hash
                        else "missing"
                    ),
                    "token_hash": token_hash,
                    "lat": geo.get("lat"),
                    "lng": geo.get("lng"),
                    "reason": _to_text(scan.get("reason") or "").strip(),
                    "chain_status": "onchain",
                    "proof_hash": _to_text(row.get("proof_hash") or "").strip(),
                }
            )
            continue

        if proof_type == "meshpeg" or trip_action == "meshpeg.verify":
            mesh = _as_dict(sd.get("meshpeg") or sd.get("meshpeg_payload") or {})
            meshpeg_entries.append(
                {
                    "item_uri": item_uri,
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                    "proof_hash": _to_text(row.get("proof_hash") or "").strip(),
                    "created_at": _display_time(mesh.get("created_at") or sd.get("trip_executed_at") or row.get("created_at")),
                    "status": _to_text(mesh.get("status") or row.get("result") or "").strip().upper(),
                    "mesh_volume": mesh.get("mesh_volume") or mesh.get("volume"),
                    "design_quantity": mesh.get("design_quantity"),
                    "deviation_percent": mesh.get("deviation_percent"),
                    "cloud": _to_text(mesh.get("cloud") or "").strip(),
                    "bim": _to_text(mesh.get("bim") or "").strip(),
                    "chain_status": "onchain",
                }
            )
            continue

        if proof_type == "railpact" or trip_action == "formula.price":
            fp = _as_dict(sd.get("railpact") or sd.get("formula") or {})
            formula_entries.append(
                {
                    "item_uri": item_uri,
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                    "proof_hash": _to_text(row.get("proof_hash") or "").strip(),
                    "created_at": _display_time(fp.get("created_at") or sd.get("trip_executed_at") or row.get("created_at")),
                    "status": _to_text(fp.get("status") or row.get("result") or "").strip().upper(),
                    "formula": _to_text(fp.get("formula") or "").strip(),
                    "qty": fp.get("qty"),
                    "unit_price": fp.get("unit_price"),
                    "amount": fp.get("amount"),
                    "railpact_id": _to_text(fp.get("railpact_id") or "").strip(),
                    "chain_status": "onchain",
                }
            )
            continue

        if proof_type == "gateway_sync" or trip_action == "gateway.sync":
            gw = _as_dict(sd.get("gateway_sync") or sd.get("gateway") or {})
            gateway_entries.append(
                {
                    "item_uri": item_uri,
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                    "proof_hash": _to_text(row.get("proof_hash") or "").strip(),
                    "created_at": _display_time(gw.get("updated_at") or sd.get("trip_executed_at") or row.get("created_at")),
                    "total_proof_hash": _to_text(gw.get("total_proof_hash") or "").strip(),
                    "risk_score": gw.get("risk_score"),
                    "scan_entry_proof": _to_text(gw.get("scan_entry_proof") or "").strip(),
                    "chain_status": "onchain",
                }
            )
            continue

    return {
        "ok": True,
        "boq_item_uri": item_uri,
        "latest_proof_id": _to_text((latest_row or {}).get("proof_id") or ""),
        "evidence": evidence_items,
        "scan_entries": scan_entries,
        "meshpeg_entries": meshpeg_entries,
        "formula_entries": formula_entries,
        "gateway_entries": gateway_entries,
        "evidence_count": len(evidence_items),
        "chain_count": len(chain_rows),
    }

"""Internal BOQ domain helpers for evidence packaging and readiness checks."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import httpx
import io
import json
import mimetypes
import re
from typing import Any
import zipfile

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from services.api.boq_audit_engine_service import get_item_sovereign_history, run_boq_audit_engine
from services.api.did_reputation_service import build_did_reputation_summary, compute_did_reputation
from services.api.docpeg_proof_chain_service import (
    build_chain_fingerprints as docpeg_build_chain_fingerprints,
    get_proof_chain as docpeg_get_proof_chain,
)
from services.api.evidence_center_service import get_all_evidence_for_item
from services.api.labpeg_frequency_remediation_service import get_frequency_dashboard
from services.api.phygital_sealing_service import build_sealing_trip
from services.api.triprole_engine import _compute_docfinal_risk_audit, get_boq_realtime_status, trace_asset_origin
from services.api.verify_public_flow_service import get_public_verify_detail_flow


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
        match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
        return float(match.group(0)) if match else None


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


def _chain_root_hash(fingerprints: list[dict[str, Any]]) -> str:
    canonical = json.dumps(fingerprints, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _safe_name(value: str, default: str = "file.bin") -> str:
    text = str(value or "").strip()
    if not text:
        return default
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", text)
    return safe[:180] or default


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


async def download_evidence_center_zip(
    *,
    project_uri: str,
    subitem_code: str,
    proof_id: str | None,
    sb: Any,
    verify_base_url: str = "https://verify.qcspec.com",
) -> StreamingResponse:
    normalized_project_uri = _to_text(project_uri).strip()
    normalized_subitem = _to_text(subitem_code).strip()
    if not normalized_project_uri:
        raise HTTPException(400, "project_uri is required")
    if not normalized_subitem:
        raise HTTPException(400, "subitem_code is required")

    history = get_item_sovereign_history(
        sb=sb,
        project_uri=normalized_project_uri,
        subitem_code=normalized_subitem,
        max_rows=50000,
    )
    timeline = history.get("timeline") if isinstance(history.get("timeline"), list) else []
    ledger = history.get("ledger_snapshot") if isinstance(history.get("ledger_snapshot"), dict) else {}
    documents = history.get("documents") if isinstance(history.get("documents"), list) else []
    boq_item_uri = _to_text(history.get("boq_item_uri") or "").strip()

    proof_id_candidates = [
        _to_text(proof_id).strip(),
        _to_text((timeline[-1] if timeline else {}).get("proof_id")).strip(),
        _to_text(history.get("root_utxo_id") or "").strip(),
    ]
    effective_proof_id = next((pid for pid in proof_id_candidates if pid), "")

    evidence_payload: dict[str, Any] = {}
    try:
        evidence_payload = get_all_evidence_for_item(sb=sb, boq_item_uri=boq_item_uri)
    except Exception:
        evidence_payload = {}
    evidence = evidence_payload.get("evidence") if isinstance(evidence_payload.get("evidence"), list) else []
    evidence_source = "boq_chain"
    if not evidence or not bool(evidence_payload.get("ok")):
        evidence_source = "verify_detail"
    if not evidence and effective_proof_id:
        verify_detail: dict[str, Any] = {}
        try:
            verify_detail = await get_public_verify_detail_flow(
                proof_id=effective_proof_id,
                lineage_depth="item",
                sb=sb,
                verify_base_url=verify_base_url,
            )
        except Exception:
            verify_detail = {}
        evidence = verify_detail.get("evidence") if isinstance(verify_detail.get("evidence"), list) else []

    risk_audit: dict[str, Any] = {}
    total_proof_hash = ""
    if boq_item_uri:
        try:
            chain_rows = docpeg_get_proof_chain(boq_item_uri, sb)
            fingerprints = docpeg_build_chain_fingerprints(chain_rows) if chain_rows else []
            if fingerprints:
                total_proof_hash = _chain_root_hash(fingerprints)
            if chain_rows:
                risk_audit = _compute_docfinal_risk_audit(
                    sb=sb,
                    project_uri=normalized_project_uri,
                    boq_item_uri=boq_item_uri,
                    chain_rows=chain_rows,
                )
                if total_proof_hash:
                    risk_audit["total_proof_hash"] = total_proof_hash
        except Exception:
            risk_audit = {}

    max_evidence_files = 120
    max_document_files = 40
    evidence_files_manifest: list[dict[str, Any]] = []
    document_files_manifest: list[dict[str, Any]] = []

    evidence_files: list[tuple[str, bytes]] = []
    for idx, item in enumerate(evidence[:max_evidence_files], start=1):
        if not isinstance(item, dict):
            continue
        raw_name = _to_text(item.get("file_name") or item.get("id") or f"evidence_{idx}")
        file_name = _safe_name(raw_name, f"evidence_{idx}.bin")
        url = _to_text(item.get("url") or item.get("storage_url") or item.get("source_url") or "")
        blob = _fetch_binary(url)
        if blob is None:
            evidence_files_manifest.append(
                {
                    "index": idx,
                    "file_name": file_name,
                    "status": "unavailable",
                    "source_url": url,
                    "evidence_hash": _to_text(item.get("evidence_hash") or ""),
                }
            )
            continue
        ext = mimetypes.guess_extension(_to_text(item.get("content_type") or "")) or ""
        if "." not in file_name and ext:
            file_name = f"{file_name}{ext}"
        sha = hashlib.sha256(blob).hexdigest()
        evidence_files_manifest.append(
            {
                "index": idx,
                "file_name": file_name,
                "status": "ok",
                "size": len(blob),
                "sha256": sha,
                "source_url": url,
                "evidence_hash": _to_text(item.get("evidence_hash") or ""),
                "proof_id": _to_text(item.get("proof_id") or ""),
            }
        )
        evidence_files.append((f"evidence/{file_name}", blob))

    document_files: list[tuple[str, bytes]] = []
    for idx, doc in enumerate(documents[:max_document_files], start=1):
        if not isinstance(doc, dict):
            continue
        raw_name = _to_text(doc.get("file_name") or doc.get("doc_type") or f"document_{idx}")
        file_name = _safe_name(raw_name, f"document_{idx}.bin")
        url = _to_text(doc.get("storage_url") or doc.get("url") or "")
        blob = _fetch_binary(url)
        if blob is None:
            document_files_manifest.append(
                {
                    "index": idx,
                    "file_name": file_name,
                    "status": "unavailable",
                    "source_url": url,
                    "doc_type": _to_text(doc.get("doc_type") or ""),
                }
            )
            continue
        ext = mimetypes.guess_extension(_to_text(doc.get("mime_type") or "")) or ""
        if "." not in file_name and ext:
            file_name = f"{file_name}{ext}"
        sha = hashlib.sha256(blob).hexdigest()
        document_files_manifest.append(
            {
                "index": idx,
                "file_name": file_name,
                "status": "ok",
                "size": len(blob),
                "sha256": sha,
                "source_url": url,
                "doc_type": _to_text(doc.get("doc_type") or ""),
            }
        )
        document_files.append((f"documents/{file_name}", blob))

    manifest = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "project_uri": normalized_project_uri,
        "subitem_code": normalized_subitem,
        "proof_id": effective_proof_id,
        "ledger_snapshot": ledger,
        "timeline": timeline,
        "documents": documents,
        "evidence": evidence,
        "evidence_source": evidence_source,
        "risk_audit": risk_audit,
        "total_proof_hash": total_proof_hash,
        "counts": {
            "timeline": len(timeline),
            "documents": len(documents),
            "evidence": len(evidence),
            "risk_issue_count": len(risk_audit.get("issues") or []) if isinstance(risk_audit, dict) else 0,
            "evidence_files": len(evidence_files_manifest),
            "document_files": len(document_files_manifest),
            "evidence_truncated": max(0, len(evidence) - max_evidence_files),
            "documents_truncated": max(0, len(documents) - max_document_files),
        },
    }
    manifest["manifest_hash"] = hashlib.sha256(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    filename = _safe_name(f"EvidenceCenter-{normalized_subitem}.zip", "EvidenceCenter.zip")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, default=str))
        zf.writestr("evidence/manifest.json", json.dumps(evidence_files_manifest, ensure_ascii=False, indent=2, default=str))
        zf.writestr("documents/manifest.json", json.dumps(document_files_manifest, ensure_ascii=False, indent=2, default=str))
        for path, blob in evidence_files:
            zf.writestr(path, blob)
        for path, blob in document_files:
            zf.writestr(path, blob)
        zf.writestr(
            "README.txt",
            (
                "Evidence Center Package (QCSpec)\n"
                "Includes manifest, evidence files, document files, and risk audit data.\n"
                "If an entry is marked unavailable, the source URL was missing or download failed.\n"
            ),
        )
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def project_readiness_check(*, project_uri: str, sb: Any) -> dict[str, Any]:
    normalized_project_uri = _to_text(project_uri).strip()
    if not normalized_project_uri:
        raise HTTPException(400, "project_uri is required")

    try:
        rows = (
            sb.table("proof_utxo")
            .select("proof_id,proof_type,result,state_data,created_at,segment_uri,spent")
            .eq("project_uri", normalized_project_uri)
            .order("created_at", desc=False)
            .limit(30000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(502, f"failed to load project proofs: {exc}") from exc

    leaf_total = 0
    group_total = 0
    linked_gate_leaf = 0
    specdict_leaf = 0
    with_children_merkle = 0
    proof_type_counts: dict[str, int] = {}
    inspection_total = 0
    inspection_pass = 0
    inspection_with_geo = 0
    inspection_with_ntp = 0
    inspection_with_evidence = 0
    lab_total = 0
    lab_pass = 0
    payment_total = 0
    payment_pass = 0
    railpact_instruction_count = 0
    doc_count = 0
    docfinal_count = 0
    scan_confirm_count = 0
    variation_count = 0

    for row in rows:
        if not isinstance(row, dict):
            continue
        ptype = _to_text(row.get("proof_type") or "").strip().lower()
        result = _to_text(row.get("result") or "").strip().upper()
        sd = _as_dict(row.get("state_data"))
        proof_type_counts[ptype] = int(proof_type_counts.get(ptype, 0)) + 1

        tree = _as_dict(sd.get("hierarchy_tree"))
        if tree:
            is_leaf = bool(tree.get("is_leaf")) if "is_leaf" in tree else bool(sd.get("is_leaf"))
            if is_leaf:
                leaf_total += 1
                if _to_text(sd.get("linked_gate_id") or "").strip() or _as_list(sd.get("linked_gate_ids")):
                    linked_gate_leaf += 1
                if _to_text(sd.get("spec_dict_key") or "").strip():
                    specdict_leaf += 1
            else:
                group_total += 1
                if _to_text(tree.get("children_merkle_root") or "").strip():
                    with_children_merkle += 1

        if ptype == "inspection":
            inspection_total += 1
            if result == "PASS":
                inspection_pass += 1
            geo = _as_dict(sd.get("geo_location"))
            if geo.get("lat") is not None and geo.get("lng") is not None:
                inspection_with_geo += 1
            if _as_dict(sd.get("server_timestamp_proof")):
                inspection_with_ntp += 1
            if _as_list(sd.get("evidence_hashes")):
                inspection_with_evidence += 1
        if ptype == "lab":
            lab_total += 1
            if result == "PASS":
                lab_pass += 1
        if ptype == "payment":
            payment_total += 1
            if result == "PASS":
                payment_pass += 1
        if ptype == "payment_instruction":
            railpact_instruction_count += 1
        if ptype == "document":
            doc_count += 1
        if "docfinal" in ptype:
            docfinal_count += 1
        if _to_text(sd.get("trip_action") or "").strip() == "variation.record" or ptype == "variation":
            variation_count += 1
        if _as_list(sd.get("scan_confirmations")):
            scan_confirm_count += 1

    try:
        realtime = get_boq_realtime_status(sb=sb, project_uri=normalized_project_uri, limit=5000)
    except Exception:
        realtime = {"summary": {}, "items": [], "ok": False}
    try:
        boq_audit = run_boq_audit_engine(
            sb=sb,
            project_uri=normalized_project_uri,
            subitem_code="",
            max_rows=50000,
            limit_items=2000,
        )
    except Exception:
        boq_audit = {"summary": {}, "audits": [], "illegal_attempts": [], "ok": False}
    try:
        frequency = get_frequency_dashboard(sb=sb, project_uri=normalized_project_uri, limit_items=300)
    except Exception:
        frequency = {"summary": {}, "items": [], "ok": False}

    realtime_summary = _as_dict(realtime.get("summary"))
    audit_summary = _as_dict(boq_audit.get("summary"))
    freq_summary = _as_dict(frequency.get("summary"))
    illegal_attempt_count = int(audit_summary.get("illegal_attempt_count") or 0)
    missed_dual_pass = int(freq_summary.get("missed_check_total") or 0)
    should_check_total = int(freq_summary.get("should_check_total") or 0)

    inspection_geo_ratio = 0.0 if inspection_total <= 0 else float(inspection_with_geo) / float(inspection_total)
    inspection_ntp_ratio = 0.0 if inspection_total <= 0 else float(inspection_with_ntp) / float(inspection_total)
    inspection_evidence_ratio = 0.0 if inspection_total <= 0 else float(inspection_with_evidence) / float(inspection_total)
    realtime_item_count = int(realtime_summary.get("item_count") or realtime_summary.get("boq_item_count") or 0)

    layers: list[dict[str, Any]] = [
        {
            "key": "live_boq",
            "name": "Live BOQ",
            "status": _status(
                complete=(leaf_total > 0 and group_total > 0 and realtime_item_count > 0),
                partial=(leaf_total > 0),
            ),
            "metrics": {
                "leaf_nodes": leaf_total,
                "group_nodes": group_total,
                "group_nodes_with_children_merkle": with_children_merkle,
                "realtime_item_count": realtime_item_count,
            },
        },
        {
            "key": "specdict_qcgate",
            "name": "SpecDict and QCGate",
            "status": _status(
                complete=(leaf_total > 0 and linked_gate_leaf >= leaf_total and specdict_leaf > 0),
                partial=(linked_gate_leaf > 0 or specdict_leaf > 0),
            ),
            "metrics": {
                "leaf_nodes": leaf_total,
                "leaf_with_gate_binding": linked_gate_leaf,
                "leaf_with_specdict_binding": specdict_leaf,
            },
        },
        {
            "key": "docpeg_documents",
            "name": "DocPeg Documents",
            "status": _status(
                complete=(docfinal_count > 0 and (doc_count > 0 or inspection_with_evidence > 0)),
                partial=(docfinal_count > 0 or doc_count > 0 or inspection_with_evidence > 0),
            ),
            "metrics": {
                "docfinal_proofs": docfinal_count,
                "document_proofs": doc_count,
                "inspection_with_evidence": inspection_with_evidence,
                "scan_confirmed_records": scan_confirm_count,
            },
        },
        {
            "key": "field_execution_qcspec",
            "name": "Field Execution",
            "status": _status(
                complete=(inspection_pass > 0 and inspection_geo_ratio >= 0.8 and inspection_ntp_ratio >= 0.8),
                partial=(inspection_total > 0),
            ),
            "metrics": {
                "inspection_total": inspection_total,
                "inspection_pass": inspection_pass,
                "geo_coverage_ratio": round(inspection_geo_ratio, 4),
                "ntp_coverage_ratio": round(inspection_ntp_ratio, 4),
                "evidence_coverage_ratio": round(inspection_evidence_ratio, 4),
            },
        },
        {
            "key": "labpeg_dual_gate",
            "name": "LabPeg Dual Gate",
            "status": _status(
                complete=(should_check_total > 0 and missed_dual_pass == 0 and lab_pass > 0),
                partial=(lab_total > 0 or should_check_total > 0),
            ),
            "metrics": {
                "lab_total": lab_total,
                "lab_pass": lab_pass,
                "expected_dual_checks": should_check_total,
                "missed_dual_checks": missed_dual_pass,
            },
        },
        {
            "key": "finance_erp_railpact",
            "name": "Finance and RailPact",
            "status": _status(
                complete=(payment_pass > 0 and railpact_instruction_count > 0 and illegal_attempt_count == 0),
                partial=(payment_total > 0 or railpact_instruction_count > 0),
            ),
            "metrics": {
                "payment_total": payment_total,
                "payment_pass": payment_pass,
                "railpact_instruction_count": railpact_instruction_count,
                "illegal_attempt_count": illegal_attempt_count,
            },
        },
        {
            "key": "audit_reconciliation",
            "name": "Audit Reconciliation",
            "status": _status(
                complete=(int(audit_summary.get("item_count") or 0) > 0 and illegal_attempt_count == 0),
                partial=(int(audit_summary.get("item_count") or 0) > 0),
            ),
            "metrics": {
                "audited_items": int(audit_summary.get("item_count") or 0),
                "illegal_attempt_count": illegal_attempt_count,
                "variation_records": variation_count,
            },
        },
    ]

    score = 0.0
    for layer in layers:
        state = _to_text(layer.get("status")).strip()
        if state == "complete":
            score += 1.0
        elif state == "partial":
            score += 0.5
    readiness_percent = round((score / max(1, len(layers))) * 100.0, 2)
    overall_status = "complete" if readiness_percent >= 95 else ("partial" if readiness_percent >= 40 else "missing")

    return {
        "ok": True,
        "project_uri": normalized_project_uri,
        "overall_status": overall_status,
        "readiness_percent": readiness_percent,
        "layers": layers,
        "raw_summary": {
            "proof_type_counts": proof_type_counts,
            "realtime": realtime_summary,
            "boq_audit": audit_summary,
            "frequency": freq_summary,
        },
    }


def _unique_rows(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        token_parts = [str(row.get(k) or "").strip() for k in keys]
        token = "|".join(token_parts).strip("|")
        if not token:
            token = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
        if token in seen:
            continue
        seen.add(token)
        out.append(row)
    return out


def _build_dispute_info(*, item_uri: str, sb: Any) -> dict[str, Any]:
    dispute_info: dict[str, Any] = {}
    try:
        disputes = (
            sb.table("proof_utxo")
            .select("proof_id,created_at,spent,state_data")
            .eq("segment_uri", item_uri)
            .eq("proof_type", "dispute")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
            .data
            or []
        )
    except Exception:
        disputes = []
    if disputes:
        open_row = next((row for row in disputes if not bool(row.get("spent"))), None)
        latest_row = disputes[0]
        open_sd = _as_dict((open_row or {}).get("state_data"))
        latest_sd = _as_dict((latest_row or {}).get("state_data"))
        dispute_info = {
            "open": bool(open_row),
            "open_proof_id": _to_text((open_row or {}).get("proof_id") or "").strip(),
            "open_created_at": _to_text((open_row or {}).get("created_at") or "").strip(),
            "open_conflict": _as_dict(open_sd.get("conflict")),
            "latest_proof_id": _to_text((latest_row or {}).get("proof_id") or "").strip(),
            "latest_created_at": _to_text((latest_row or {}).get("created_at") or "").strip(),
            "latest_conflict": _as_dict(latest_sd.get("conflict")),
        }
    return dispute_info


def _smu_id_from_item_code(item_code: str) -> str:
    token = _to_text(item_code).strip().split("/")[-1]
    return token.split("-")[0] if "-" in token else token


def _extract_executor_did_from_row(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    did_gate = _as_dict(sd.get("did_gate"))
    for candidate in (
        did_gate.get("user_did"),
        sd.get("executor_did"),
        sd.get("operator_did"),
        sd.get("actor_did"),
    ):
        did = _to_text(candidate).strip()
        if did.startswith("did:"):
            return did
    return ""


def _load_rows_by_proof_ids(*, proof_ids: list[str], sb: Any) -> list[dict[str, Any]]:
    ids = [x for x in (_to_text(pid).strip() for pid in proof_ids) if x]
    if not ids:
        return []
    out: list[dict[str, Any]] = []
    step = 200
    for i in range(0, len(ids), step):
        chunk = ids[i : i + step]
        try:
            rows = sb.table("proof_utxo").select("*").in_("proof_id", chunk).execute().data or []
            for row in rows:
                if isinstance(row, dict):
                    out.append(row)
        except Exception:
            continue
    return out


def get_evidence_center_evidence(
    *,
    project_uri: str | None,
    subitem_code: str | None,
    boq_item_uri: str | None,
    smu_id: str | None,
    sb: Any,
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    scope_smu_id = _to_text(smu_id).strip()
    if scope_smu_id:
        if not p_uri:
            raise HTTPException(400, "project_uri is required when smu_id is provided")
        realtime = get_boq_realtime_status(sb=sb, project_uri=p_uri, limit=10000)
        items = [
            _as_dict(x)
            for x in _as_list(realtime.get("items"))
            if _to_text(_as_dict(x).get("item_no") or "").strip().startswith(scope_smu_id)
        ]
        if not items:
            raise HTTPException(404, f"no BOQ items found under smu_id={scope_smu_id}")

        timeline: list[dict[str, Any]] = []
        documents: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        scan_entries: list[dict[str, Any]] = []
        meshpeg_entries: list[dict[str, Any]] = []
        formula_entries: list[dict[str, Any]] = []
        gateway_entries: list[dict[str, Any]] = []
        risk_issues: list[dict[str, Any]] = []
        total_hash_items: list[dict[str, Any]] = []
        risk_scores: list[float] = []
        dispute_items: list[dict[str, Any]] = []
        evidence_item_codes: set[str] = set()
        settled_leaf_count = 0
        latest_proof_id = ""

        ledger = {
            "design_quantity": 0.0,
            "approved_quantity": 0.0,
            "contract_quantity": 0.0,
            "settled_quantity": 0.0,
            "consumed_quantity": 0.0,
        }

        for row in items:
            item_no = _to_text(row.get("item_no") or "").strip()
            item_uri = _to_text(row.get("boq_item_uri") or "").strip()
            if int(_to_float(row.get("settlement_count")) or 0) > 0:
                settled_leaf_count += 1
            for field in ("design_quantity", "approved_quantity", "contract_quantity", "settled_quantity", "consumed_quantity"):
                ledger[field] = float(ledger.get(field) or 0.0) + float(_to_float(row.get(field)) or 0.0)

            if not item_no or not item_uri:
                continue
            try:
                history = get_item_sovereign_history(
                    sb=sb,
                    project_uri=p_uri,
                    subitem_code=item_no,
                    max_rows=50000,
                )
            except Exception:
                history = {}

            for entry in _as_list(history.get("timeline")):
                one = _as_dict(entry)
                one.setdefault("item_no", item_no)
                one.setdefault("boq_item_uri", item_uri)
                timeline.append(one)
                pid = _to_text(one.get("proof_id") or "").strip()
                if pid:
                    latest_proof_id = pid

            for entry in _as_list(history.get("documents")):
                one = _as_dict(entry)
                one.setdefault("item_no", item_no)
                one.setdefault("boq_item_uri", item_uri)
                documents.append(one)

            risk_audit = _as_dict(history.get("risk_audit"))
            score = _to_float(risk_audit.get("risk_score"))
            if score is not None:
                risk_scores.append(float(score))
            for issue in _as_list(risk_audit.get("issues")):
                if isinstance(issue, dict):
                    merged = dict(issue)
                    merged.setdefault("item_no", item_no)
                    merged.setdefault("boq_item_uri", item_uri)
                    risk_issues.append(merged)
            total_hash = _to_text(history.get("total_proof_hash") or "").strip()
            if total_hash:
                total_hash_items.append({"item_no": item_no, "boq_item_uri": item_uri, "total_proof_hash": total_hash})

            ev_payload = get_all_evidence_for_item(sb=sb, boq_item_uri=item_uri)
            ev_list = _as_list(ev_payload.get("evidence"))
            if ev_list:
                evidence_item_codes.add(item_no)
            for entry in ev_list:
                one = _as_dict(entry)
                one.setdefault("item_no", item_no)
                one.setdefault("boq_item_uri", item_uri)
                evidence.append(one)
            for entry in _as_list(ev_payload.get("scan_entries")):
                one = _as_dict(entry)
                one.setdefault("item_no", item_no)
                one.setdefault("boq_item_uri", item_uri)
                scan_entries.append(one)
            for entry in _as_list(ev_payload.get("meshpeg_entries")):
                one = _as_dict(entry)
                one.setdefault("item_no", item_no)
                one.setdefault("boq_item_uri", item_uri)
                meshpeg_entries.append(one)
            for entry in _as_list(ev_payload.get("formula_entries")):
                one = _as_dict(entry)
                one.setdefault("item_no", item_no)
                one.setdefault("boq_item_uri", item_uri)
                formula_entries.append(one)
            for entry in _as_list(ev_payload.get("gateway_entries")):
                one = _as_dict(entry)
                one.setdefault("item_no", item_no)
                one.setdefault("boq_item_uri", item_uri)
                gateway_entries.append(one)
            dispute = _build_dispute_info(item_uri=item_uri, sb=sb)
            if dispute:
                dispute["item_no"] = item_no
                dispute["boq_item_uri"] = item_uri
                dispute_items.append(dispute)

        timeline = sorted(_unique_rows(timeline, ("proof_id", "created_at", "item_no")), key=lambda x: _to_text(x.get("created_at") or ""))
        documents = sorted(_unique_rows(documents, ("proof_id", "created_at", "item_no")), key=lambda x: _to_text(x.get("created_at") or ""))
        evidence = _unique_rows(evidence, ("proof_id", "evidence_hash", "file_name", "item_no"))
        scan_entries = _unique_rows(scan_entries, ("proof_id", "token_hash", "created_at", "item_no"))
        meshpeg_entries = _unique_rows(meshpeg_entries, ("proof_id", "created_at", "item_no"))
        formula_entries = _unique_rows(formula_entries, ("proof_id", "created_at", "item_no"))
        gateway_entries = _unique_rows(gateway_entries, ("proof_id", "created_at", "item_no"))

        leaf_total = len(items)
        evidence_leaf_count = len(evidence_item_codes)
        settlement_coverage = 0.0 if leaf_total <= 0 else float(settled_leaf_count) / float(leaf_total)
        evidence_coverage = 0.0 if leaf_total <= 0 else float(evidence_leaf_count) / float(leaf_total)
        completeness_score = round(max(0.0, min(100.0, ((settlement_coverage * 0.5) + (evidence_coverage * 0.5)) * 100.0)), 2)
        settlement_risk_score = round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0.0
        total_proof_hash = _chain_root_hash(
            sorted(total_hash_items, key=lambda x: (_to_text(x.get("item_no") or ""), _to_text(x.get("total_proof_hash") or "")))
        ) if total_hash_items else ""
        did_reputation: dict[str, Any] = {}
        timeline_proof_ids = [
            _to_text(_as_dict(x).get("proof_id") or "").strip()
            for x in timeline
            if _to_text(_as_dict(x).get("proof_id") or "").strip()
        ]
        if timeline_proof_ids:
            rows = _load_rows_by_proof_ids(proof_ids=timeline_proof_ids, sb=sb)
            if rows:
                try:
                    did_reputation = build_did_reputation_summary(
                        sb=sb,
                        project_uri=p_uri,
                        chain_rows=rows,
                        window_days=90,
                    )
                except Exception:
                    did_reputation = {}

        asset_origin: dict[str, Any] = {}
        trace_target = next(
            (_as_dict(x) for x in items if _to_text(_as_dict(x).get("latest_settlement_proof_id") or "").strip()),
            _as_dict(items[0]) if items else {},
        )
        trace_item_uri = _to_text(trace_target.get("boq_item_uri") or "").strip()
        trace_proof = _to_text(trace_target.get("latest_settlement_proof_id") or trace_target.get("sign_candidate_proof_id") or "").strip()
        if trace_item_uri:
            try:
                asset_origin = trace_asset_origin(
                    sb=sb,
                    utxo_id=trace_proof,
                    boq_item_uri=trace_item_uri,
                    project_uri=p_uri,
                )
            except Exception:
                asset_origin = {}
        smu_statement = (
            f"SMU {scope_smu_id} contract_total {round(float(ledger.get('contract_quantity') or 0.0), 4)}, "
            f"settled_total {round(float(ledger.get('settled_quantity') or 0.0), 4)}."
        )
        sample_statement = _to_text(_as_dict(asset_origin).get("statement") or "").strip()
        if sample_statement:
            smu_statement = f"{smu_statement} Sample item: {sample_statement}"
        sealing_trip = {}
        if total_proof_hash:
            try:
                sealing_trip = build_sealing_trip(
                    total_proof_hash=total_proof_hash,
                    project_uri=p_uri,
                    boq_item_uri=f"{p_uri.rstrip('/')}/smu/{scope_smu_id}",
                    smu_id=scope_smu_id,
                )
            except Exception:
                sealing_trip = {}

        ledger = {k: round(float(v), 4) for k, v in ledger.items()}
        return {
            "ok": True,
            "scope": "smu",
            "project_uri": p_uri,
            "smu_id": scope_smu_id,
            "proof_id": latest_proof_id,
            "latest_proof_id": latest_proof_id,
            "boq_item_uris": [_to_text(x.get("boq_item_uri") or "").strip() for x in items if _to_text(x.get("boq_item_uri") or "").strip()],
            "ledger": ledger,
            "timeline": timeline,
            "documents": documents,
            "evidence": evidence,
            "scan_entries": scan_entries,
            "meshpeg_entries": meshpeg_entries,
            "formula_entries": formula_entries,
            "gateway_entries": gateway_entries,
            "evidence_source": "smu_aggregate",
            "total_proof_hash": total_proof_hash,
            "risk_audit": {
                "risk_score": settlement_risk_score,
                "issues": risk_issues[:500],
                "total_proof_hash": total_proof_hash,
                "did_reputation": did_reputation,
                "sampling_multiplier": _to_float(_as_dict(did_reputation).get("sampling_multiplier")) or 1.0,
            },
            "evidence_completeness": {
                "score": completeness_score,
                "leaf_total": leaf_total,
                "settled_leaf_count": settled_leaf_count,
                "evidence_leaf_count": evidence_leaf_count,
                "settlement_coverage_ratio": round(settlement_coverage, 6),
                "evidence_coverage_ratio": round(evidence_coverage, 6),
            },
            "settlement_risk_score": settlement_risk_score,
            "did_reputation": did_reputation,
            "asset_origin": {
                "scope": "smu",
                "smu_id": scope_smu_id,
                "summary": {
                    "contract_quantity_total": round(float(ledger.get("contract_quantity") or 0.0), 6),
                    "settled_quantity_total": round(float(ledger.get("settled_quantity") or 0.0), 6),
                    "delta_total": round(float(ledger.get("settled_quantity") or 0.0) - float(ledger.get("contract_quantity") or 0.0), 6),
                },
                "sample_item": asset_origin,
                "statement": smu_statement,
            },
            "asset_origin_statement": smu_statement,
            "sealing_trip": sealing_trip,
            "consensus_dispute": {
                "open": any(bool(_as_dict(x).get("open")) for x in dispute_items),
                "items": dispute_items[:100],
            },
        }

    item_uri = _to_text(boq_item_uri).strip()
    code = _to_text(subitem_code).strip()
    if not p_uri and item_uri:
        marker = "/boq/"
        idx = item_uri.find(marker)
        if idx > 0:
            p_uri = f"{item_uri[:idx].rstrip('/')}/"
    if not item_uri:
        if not p_uri or not code:
            raise HTTPException(400, "boq_item_uri or (project_uri + subitem_code) is required")
        history = get_item_sovereign_history(sb=sb, project_uri=p_uri, subitem_code=code, max_rows=50000)
        item_uri = _to_text(history.get("boq_item_uri") or "").strip()
    else:
        history = {}
        if p_uri and code:
            try:
                history = get_item_sovereign_history(sb=sb, project_uri=p_uri, subitem_code=code, max_rows=50000)
            except Exception:
                history = {}
    if not item_uri:
        raise HTTPException(404, "boq_item_uri not resolved")

    if not history:
        if p_uri and not code:
            code = _to_text(item_uri.rstrip("/").split("/")[-1]).strip()
        if p_uri and code:
            try:
                history = get_item_sovereign_history(sb=sb, project_uri=p_uri, subitem_code=code, max_rows=50000)
            except Exception:
                history = {}

    payload = get_all_evidence_for_item(sb=sb, boq_item_uri=item_uri)
    payload["scope"] = "item"
    payload["boq_item_uri"] = item_uri
    payload["evidence_source"] = "boq_chain"
    payload["timeline"] = _as_list(history.get("timeline"))
    payload["documents"] = _as_list(history.get("documents"))
    payload["ledger"] = _as_dict(history.get("ledger_snapshot"))
    payload["risk_audit"] = _as_dict(history.get("risk_audit"))
    payload["total_proof_hash"] = _to_text(history.get("total_proof_hash") or "").strip()
    payload["proof_id"] = _to_text(history.get("root_utxo_id") or "").strip()
    payload["latest_proof_id"] = _to_text((_as_list(history.get("timeline"))[-1] if _as_list(history.get("timeline")) else {}).get("proof_id") or "").strip()
    payload["consensus_dispute"] = _build_dispute_info(item_uri=item_uri, sb=sb)
    item_code = _to_text(code or item_uri.rstrip("/").split("/")[-1]).strip()
    item_smu_id = _smu_id_from_item_code(item_code)
    trace_target_proof = _to_text(payload.get("latest_proof_id") or payload.get("proof_id") or "").strip()
    asset_origin: dict[str, Any] = {}
    try:
        asset_origin = trace_asset_origin(sb=sb, utxo_id=trace_target_proof, boq_item_uri=item_uri, project_uri=p_uri)
    except Exception:
        asset_origin = {}

    risk_audit = _as_dict(payload.get("risk_audit"))
    did_reputation = _as_dict(risk_audit.get("did_reputation"))
    if not did_reputation and p_uri:
        chain_proof_ids: list[str] = []
        seen_proofs: set[str] = set()
        timeline_rows = _as_list(payload.get("timeline"))
        for entry in timeline_rows:
            pid = _to_text(_as_dict(entry).get("proof_id") or "").strip()
            if not pid or pid in seen_proofs:
                continue
            seen_proofs.add(pid)
            chain_proof_ids.append(pid)
        for candidate in (
            _to_text(payload.get("latest_proof_id") or "").strip(),
            _to_text(payload.get("proof_id") or "").strip(),
        ):
            if candidate and candidate not in seen_proofs:
                seen_proofs.add(candidate)
                chain_proof_ids.append(candidate)

        chain_rows = _load_rows_by_proof_ids(proof_ids=chain_proof_ids, sb=sb)
        try:
            did_reputation = build_did_reputation_summary(
                sb=sb,
                project_uri=p_uri,
                chain_rows=chain_rows,
                window_days=90,
            )
        except Exception:
            did_reputation = {}

        if not did_reputation:
            did_candidate = ""
            latest_proof = _to_text(payload.get("latest_proof_id") or payload.get("proof_id") or "").strip()
            if latest_proof:
                rows = _load_rows_by_proof_ids(proof_ids=[latest_proof], sb=sb)
                if rows:
                    did_candidate = _extract_executor_did_from_row(rows[0])
            if did_candidate.startswith("did:"):
                try:
                    did_reputation = compute_did_reputation(
                        sb=sb,
                        project_uri=p_uri,
                        participant_did=did_candidate,
                        window_days=90,
                    )
                except Exception:
                    did_reputation = {}
    sealing_trip = {}
    total_hash = _to_text(payload.get("total_proof_hash") or "").strip()
    if total_hash:
        try:
            sealing_trip = build_sealing_trip(
                total_proof_hash=total_hash,
                project_uri=p_uri,
                boq_item_uri=item_uri,
                smu_id=item_smu_id,
            )
        except Exception:
            sealing_trip = {}
    payload["asset_origin"] = asset_origin
    payload["asset_origin_statement"] = _to_text(_as_dict(asset_origin).get("statement") or "").strip()
    payload["did_reputation"] = did_reputation
    payload["sealing_trip"] = sealing_trip
    risk_audit["did_reputation"] = did_reputation
    if "sampling_multiplier" not in risk_audit:
        risk_audit["sampling_multiplier"] = _to_float(_as_dict(did_reputation).get("sampling_multiplier")) or 1.0
    payload["risk_audit"] = risk_audit
    return payload

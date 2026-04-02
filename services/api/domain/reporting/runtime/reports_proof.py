"""
Report proof loading and normalization helpers.
services/api/reports_proof_service.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from supabase import Client

REPORT_TEMPLATE_BY_TYPE = {
    "inspection": "01_inspection_report.docx",
    "lab": "02_lab_report.docx",
    "monthly_summary": "03_monthly_summary.docx",
    "final_archive": "04_final_archive_cover.docx",
}


def guess_executor_uri(project_uri: str, person: Optional[str]) -> str:
    root = str(project_uri or "").strip()
    for marker in ("/highway/", "/bridge/", "/urban/", "/road/", "/tunnel/"):
        idx = root.find(marker)
        if idx > 0:
            root = root[: idx + 1]
            break
    if not root.endswith("/"):
        root += "/"
    person_name = str(person or "").strip()
    if person_name:
        return f"{root}executor/{person_name}/"
    return f"{root}executor/system/"


def normalize_report_type(raw: Optional[str]) -> str:
    text = str(raw or "").strip().lower()
    alias = {
        "inspection_report": "inspection",
        "qcspec": "inspection",
        "quality": "inspection",
        "lab_report": "lab",
        "laboratory": "lab",
        "monthly": "monthly_summary",
        "summary": "monthly_summary",
        "archive": "final_archive",
        "final": "final_archive",
        "final_archive_cover": "final_archive",
    }
    normalized = alias.get(text, text)
    return normalized if normalized in REPORT_TEMPLATE_BY_TYPE else "inspection"


def proof_types_for_report(report_type: str) -> list[str]:
    mapping = {
        "inspection": ["inspection"],
        "lab": ["lab"],
        "monthly_summary": ["inspection", "lab"],
        "final_archive": ["archive", "inspection", "lab"],
    }
    return mapping.get(normalize_report_type(report_type), ["inspection"])


def template_for_report(report_type: str) -> str:
    normalized = normalize_report_type(report_type)
    return REPORT_TEMPLATE_BY_TYPE.get(normalized, REPORT_TEMPLATE_BY_TYPE["inspection"])


def proof_matches_location(proof: dict[str, Any], location: Optional[str]) -> bool:
    if not location:
        return True
    sd = proof.get("state_data") if isinstance(proof.get("state_data"), dict) else {}
    proof_loc = str(sd.get("location") or sd.get("stake") or "").strip()
    return proof_loc == str(location).strip()


def is_business_inspection_proof(proof: dict[str, Any]) -> bool:
    sd = proof.get("state_data") if isinstance(proof.get("state_data"), dict) else {}
    proof_type = str(proof.get("proof_type") or "").strip().lower()
    if proof_type and proof_type != "inspection":
        return False

    t = str(sd.get("test_type") or sd.get("type") or "").strip().lower()
    tn = str(sd.get("test_name") or sd.get("type_name") or "").strip().lower()
    token = f"{t} {tn}"
    if t:
        return True

    has_values = any(
        sd.get(key) not in (None, "", [])
        for key in ("value", "values", "standard", "design")
    )
    if has_values:
        return True

    return any(
        k in token
        for k in (
            "rebar",
            "flatness",
            "iri",
            "crack",
            "rut",
            "钢筋",
            "平整度",
            "裂缝",
            "车辙",
            "间距",
            "骨架",
            "保护层",
        )
    )


def filter_inspection_template_proofs(proofs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not proofs:
        return proofs
    filtered = [p for p in proofs if is_business_inspection_proof(p)]
    return filtered if filtered else proofs


def proof_inspection_id(row: dict[str, Any]) -> str:
    sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
    for key in ("inspection_id", "source_inspection_id", "id"):
        value = str(sd.get(key) or "").strip()
        if value:
            return value
    return ""


def dedupe_proofs_for_export(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows

    sorted_rows = sorted(
        [r for r in rows if isinstance(r, dict)],
        key=lambda x: str(x.get("created_at") or ""),
    )
    latest_by_key: dict[str, dict[str, Any]] = {}
    for row in sorted_rows:
        key = proof_inspection_id(row) or str(row.get("proof_id") or "").strip()
        if not key:
            continue
        latest_by_key[key] = row

    deduped = list(latest_by_key.values())
    deduped.sort(key=lambda x: str(x.get("created_at") or ""))
    return deduped


def load_rebar_live_proofs(
    sb: Client,
    *,
    project_uri: str,
    records: list[dict[str, Any]],
    location: Optional[str],
    inspected_from: Optional[str],
    inspected_to: Optional[str],
    proof_types: Optional[list[str]] = None,
    report_type: str = "inspection",
) -> list[dict[str, Any]]:
    target_types = [str(x).strip().lower() for x in (proof_types or ["inspection"]) if str(x).strip()]
    if not target_types:
        target_types = ["inspection"]
    normalized_report_type = normalize_report_type(report_type)
    rows: list[dict[str, Any]] = []
    try:
        q = sb.table("proof_utxo").select("*").eq("project_uri", project_uri).order("created_at", desc=False).limit(1000)
        if len(target_types) == 1:
            q = q.eq("proof_type", target_types[0])
        else:
            q = q.in_("proof_type", target_types)
        if inspected_from:
            q = q.gte("created_at", inspected_from)
        if inspected_to:
            q = q.lte("created_at", inspected_to)
        rows = q.execute().data or []
    except Exception:
        rows = []

    rows = [x for x in rows if proof_matches_location(x, location)]
    if rows:
        record_ids = {
            str(r.get("id") or "").strip()
            for r in (records or [])
            if str(r.get("id") or "").strip()
        }
        record_proof_ids = {
            str(r.get("proof_id") or "").strip()
            for r in (records or [])
            if str(r.get("proof_id") or "").strip()
        }

        if record_ids or record_proof_ids:
            strict_rows: list[dict[str, Any]] = []
            for row in rows:
                proof_id = str(row.get("proof_id") or "").strip()
                inspection_id = proof_inspection_id(row)
                if record_proof_ids and proof_id in record_proof_ids:
                    strict_rows.append(row)
                    continue
                if record_ids and inspection_id and inspection_id in record_ids:
                    strict_rows.append(row)

            if strict_rows:
                return dedupe_proofs_for_export(strict_rows)
            rows = []
        else:
            def _looks_like_business_proof(row: dict[str, Any]) -> bool:
                sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
                return any(
                    sd.get(key) not in (None, "", [])
                    for key in ("value", "values", "type", "type_name", "design", "standard")
                )

            legacy_rows = [x for x in rows if _looks_like_business_proof(x)]
            if legacy_rows:
                return dedupe_proofs_for_export(legacy_rows)
            rows = []

    fallback: list[dict[str, Any]] = []
    for rec in records:
        rid = str(rec.get("id") or "")
        rec_proof_id = str(rec.get("proof_id") or f"GP-PROOF-FB-{rid[:8].upper()}")
        project_uri_clean = str(project_uri or "").strip()
        v_uri = (
            str(rec.get("v_uri") or "").strip()
            or f"{project_uri_clean.rstrip('/')}/{normalized_report_type}/{rid}/"
        )
        fallback.append(
            {
                "proof_id": rec_proof_id,
                "proof_hash": str(rec.get("proof_hash") or ""),
                "project_uri": project_uri_clean,
                "segment_uri": None,
                "proof_type": target_types[0],
                "result": str(rec.get("result") or "PENDING").upper(),
                "gitpeg_anchor": None,
                "signed_by": [
                    {
                        "executor_uri": guess_executor_uri(project_uri_clean, rec.get("person")),
                        "role": "AI",
                        "ordosign_hash": "",
                    }
                ],
                "created_at": str(rec.get("inspected_at") or datetime.utcnow().isoformat()),
                "state_data": {
                    "inspection_id": rid,
                    "v_uri": v_uri,
                    "location": rec.get("location"),
                    "type": rec.get("type") or normalized_report_type,
                    "type_name": rec.get("type_name") or normalized_report_type,
                    "value": rec.get("value"),
                    "standard_value": rec.get("standard"),
                    "standard": rec.get("standard"),
                    "standard_op": (
                        ">="
                        if any(
                            k in f"{str(rec.get('type') or '').lower()} {str(rec.get('type_name') or '').lower()}"
                            for k in ("compaction", "density", "压实度", "压实")
                        )
                        else "<="
                    ),
                    "unit": rec.get("unit"),
                    "result": rec.get("result"),
                    "remark": rec.get("remark"),
                },
            }
        )
    return fallback


def proof_utxo_row_to_render_proof(row: dict[str, Any], *, report_type: str = "inspection") -> dict[str, Any]:
    sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
    sd_out = dict(sd)

    test_type = str(sd_out.get("test_type") or sd_out.get("type") or "").strip()
    test_name = str(sd_out.get("test_name") or sd_out.get("type_name") or "").strip()
    if not test_type:
        test_type = test_name or str(report_type or "inspection")
    if not test_name:
        test_name = test_type
    sd_out["test_type"] = test_type
    sd_out["type"] = test_type
    sd_out["test_name"] = test_name
    sd_out["type_name"] = test_name

    if sd_out.get("standard_value") in (None, ""):
        if sd_out.get("standard") not in (None, ""):
            sd_out["standard_value"] = sd_out.get("standard")
        elif sd_out.get("design") not in (None, ""):
            sd_out["standard_value"] = sd_out.get("design")

    raw_op = str(
        sd_out.get("standard_op")
        or sd_out.get("standard_operator")
        or sd_out.get("operator")
        or sd_out.get("comparator")
        or sd_out.get("compare")
        or ""
    ).strip()
    if not raw_op:
        token = f"{test_type} {test_name}".lower()
        if sd_out.get("limit") not in (None, "", "-"):
            sd_out["standard_op"] = "±"
        elif any(k in token for k in ("compaction", "density", "压实度", "压实")):
            sd_out["standard_op"] = ">="
        else:
            sd_out["standard_op"] = "<="
    else:
        sd_out["standard_op"] = raw_op

    if sd_out.get("values") in (None, "") and sd_out.get("value") not in (None, ""):
        sd_out["values"] = [sd_out.get("value")]

    signed = row.get("signed_by")
    if isinstance(signed, dict):
        signed = [signed]
    if not isinstance(signed, list):
        signed = []
    normalized_signed: list[dict[str, Any]] = []
    for item in signed:
        if not isinstance(item, dict):
            continue
        entry = dict(item)
        uri = str(entry.get("executor_uri") or row.get("owner_uri") or "").strip()
        if not entry.get("executor_id"):
            entry["executor_id"] = uri.rstrip("/").split("/")[-1] if uri else "unknown"
        normalized_signed.append(entry)
    signed = normalized_signed

    if not signed:
        owner_uri = str(row.get("owner_uri") or "-")
        owner_tail = owner_uri.rstrip("/").split("/")[-1] if owner_uri else ""
        signed = [
            {
                "executor_uri": owner_uri,
                "executor_id": owner_tail or "unknown",
                "ordosign_hash": str(row.get("ordosign_hash") or ""),
                "ts": str(row.get("created_at") or ""),
            }
        ]

    return {
        "proof_id": str(row.get("proof_id") or ""),
        "proof_hash": str(row.get("proof_hash") or ""),
        "project_id": row.get("project_id"),
        "project_uri": str(row.get("project_uri") or ""),
        "segment_uri": str(row.get("segment_uri") or sd_out.get("segment_uri") or ""),
        "proof_type": str(row.get("proof_type") or report_type or "inspection"),
        "result": str(row.get("result") or sd_out.get("result") or "PENDING"),
        "gitpeg_anchor": row.get("gitpeg_anchor"),
        "signed_by": signed,
        "created_at": str(row.get("created_at") or ""),
        "state_data": sd_out,
    }


def project_meta_from_proof_rows(
    sb: Client,
    *,
    rows: list[dict[str, Any]],
    report_type: str,
) -> tuple[dict[str, Any], str | None, str | None]:
    first = rows[0] if rows else {}
    project_id = str(first.get("project_id") or "").strip() or None
    project_uri = str(first.get("project_uri") or "").strip()
    proj: dict[str, Any] = {}

    try:
        q = sb.table("projects").select("id, enterprise_id, v_uri, name, contract_no, supervisor")
        if project_id:
            res = q.eq("id", project_id).limit(1).execute()
            proj = (res.data or [{}])[0]
        elif project_uri:
            res = q.eq("v_uri", project_uri).limit(1).execute()
            proj = (res.data or [{}])[0]
    except Exception:
        proj = {}

    normalized_type = normalize_report_type(report_type)
    base_uri = str(proj.get("v_uri") or project_uri or "").strip()
    project_meta = {
        "name": str(proj.get("name") or ""),
        "project_name": str(proj.get("name") or ""),
        "project_uri": base_uri,
        "contract_no": str(proj.get("contract_no") or "-"),
        "stake_range": str(((first.get("state_data") or {}).get("location") if isinstance(first.get("state_data"), dict) else "") or "-"),
        "check_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "inspector": "系统自动生成",
        "tech_leader": str(proj.get("supervisor") or "-"),
        "template_name": template_for_report(normalized_type),
    }
    return project_meta, (str(proj.get("id") or "").strip() or project_id), (str(proj.get("enterprise_id") or "").strip() or None)

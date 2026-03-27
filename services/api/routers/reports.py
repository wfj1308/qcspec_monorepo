"""
QCSpec report routes
services/api/routers/reports.py
"""

from datetime import datetime
import io
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import traceback
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from postgrest.exceptions import APIError
from pydantic import BaseModel
from supabase import Client, create_client

from docx_engine import DocxEngine
from specir_engine import derive_spec_uri as specir_derive_spec_uri
from specir_engine import evaluate_measurements as specir_evaluate_measurements
from specir_engine import resolve_spec_rule as specir_resolve_spec_rule
from .proof_utxo_engine import ProofUTXOEngine

router = APIRouter()


@lru_cache(maxsize=1)
def _supabase_client_cached(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase() -> Client:
    url = str(os.getenv("SUPABASE_URL") or "").strip()
    key = str(
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    ).strip()
    if not url or not key:
        raise HTTPException(500, "Supabase not configured")
    return _supabase_client_cached(url, key)


class ReportRequest(BaseModel):
    project_id: str
    enterprise_id: str
    location: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class ReportExportRequest(BaseModel):
    project_id: str
    enterprise_id: str
    type: str = "inspection"
    format: str = "docx"
    location: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


REPORT_TEMPLATE_BY_TYPE = {
    "inspection": "01_inspection_report.docx",
    "lab": "02_lab_report.docx",
    "monthly_summary": "03_monthly_summary.docx",
    "final_archive": "04_final_archive_cover.docx",
}
REPORTS_BUCKET = str(os.getenv("SUPABASE_REPORTS_BUCKET") or "qcspec-reports").strip() or "qcspec-reports"
REPORT_FILE_URL_TTL_S = int(str(os.getenv("REPORT_FILE_URL_TTL_S") or "86400").strip() or "86400")


def _normalize_dt(raw: Optional[str], end_of_day: bool = False) -> Optional[str]:
    text = str(raw or "").strip()
    if not text:
        return None
    # YYYY-MM-DD -> explicit day boundary
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return f"{text}T23:59:59" if end_of_day else f"{text}T00:00:00"
    return text


def _extract_signed_url(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("signedURL", "signedUrl", "url"):
            value = str(payload.get(key) or "").strip()
            if value:
                return value
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("signedURL", "signedUrl", "url"):
                value = str(data.get(key) or "").strip()
                if value:
                    return value
    return ""


def _report_file_url(sb: Client, storage_path: str, fallback: str = "") -> str:
    path = str(storage_path or "").strip()
    if not path:
        return str(fallback or "")
    # Prefer signed URL to support private buckets.
    try:
        signed = sb.storage.from_(REPORTS_BUCKET).create_signed_url(path, REPORT_FILE_URL_TTL_S)
        signed_url = _extract_signed_url(signed)
        if signed_url:
            return signed_url
    except Exception:
        pass
    # Fallback for public buckets.
    try:
        public_url = sb.storage.from_(REPORTS_BUCKET).get_public_url(path)
        if isinstance(public_url, str) and public_url:
            return public_url
    except Exception:
        pass
    return str(fallback or "")


def _gen_proof(v_uri: str, data: dict) -> str:
    payload = json.dumps(
        {"uri": v_uri, "data": data, "ts": datetime.utcnow().isoformat()},
        sort_keys=True,
    )
    h = hashlib.sha256(payload.encode()).hexdigest()[:16].upper()
    return f"GP-PROOF-{h}"


def _guess_owner_uri(project_uri: str) -> str:
    root = str(project_uri or "").strip()
    for marker in ("/highway/", "/bridge/", "/urban/", "/road/", "/tunnel/"):
        idx = root.find(marker)
        if idx > 0:
            root = root[: idx + 1]
            break
    if not root.endswith("/"):
        root += "/"
    return f"{root}executor/system/"


def _insert_report_compat(sb: Client, payload: dict) -> None:
    """
    Insert report with schema compatibility:
    if PostgREST reports unknown columns (PGRST204), drop them and retry.
    """
    candidate = dict(payload)
    for _ in range(8):
        try:
            sb.table("reports").insert(candidate).execute()
            return
        except APIError as exc:
            # postgrest-py may expose payload as string instead of dict.
            raw = str(exc)
            code_match = re.search(r"'code':\s*'([^']+)'", raw)
            code = code_match.group(1) if code_match else ""
            if code != "PGRST204":
                raise
            missing_match = re.search(r"Could not find the '([^']+)' column of 'reports'", raw)
            if not missing_match:
                raise
            missing_col = missing_match.group(1)
            if missing_col not in candidate:
                raise
            candidate.pop(missing_col, None)
    raise RuntimeError("report insert failed after compatibility retries")


def _guess_executor_uri(project_uri: str, person: Optional[str]) -> str:
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


def _normalize_report_type(raw: Optional[str]) -> str:
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


def _proof_types_for_report(report_type: str) -> list[str]:
    mapping = {
        "inspection": ["inspection"],
        "lab": ["lab"],
        "monthly_summary": ["inspection", "lab"],
        "final_archive": ["archive", "inspection", "lab"],
    }
    return mapping.get(_normalize_report_type(report_type), ["inspection"])


def _template_for_report(report_type: str) -> str:
    normalized = _normalize_report_type(report_type)
    return REPORT_TEMPLATE_BY_TYPE.get(normalized, REPORT_TEMPLATE_BY_TYPE["inspection"])


def _proof_matches_location(proof: dict[str, Any], location: Optional[str]) -> bool:
    if not location:
        return True
    sd = proof.get("state_data") if isinstance(proof.get("state_data"), dict) else {}
    proof_loc = str(sd.get("location") or sd.get("stake") or "").strip()
    return proof_loc == str(location).strip()


def _is_business_inspection_proof(proof: dict[str, Any]) -> bool:
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


def _filter_inspection_template_proofs(proofs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not proofs:
        return proofs
    filtered = [p for p in proofs if _is_business_inspection_proof(p)]
    return filtered if filtered else proofs


def _proof_inspection_id(row: dict[str, Any]) -> str:
    sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
    for key in ("inspection_id", "source_inspection_id", "id"):
        value = str(sd.get(key) or "").strip()
        if value:
            return value
    return ""


def _dedupe_proofs_for_export(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Keep at most one proof per inspection for export statistics/rendering.
    If inspection_id is missing, fallback to proof_id as the uniqueness key.
    """
    if not rows:
        return rows

    sorted_rows = sorted(
        [r for r in rows if isinstance(r, dict)],
        key=lambda x: str(x.get("created_at") or ""),
    )
    latest_by_key: dict[str, dict[str, Any]] = {}
    for row in sorted_rows:
        key = _proof_inspection_id(row) or str(row.get("proof_id") or "").strip()
        if not key:
            continue
        latest_by_key[key] = row

    deduped = list(latest_by_key.values())
    deduped.sort(key=lambda x: str(x.get("created_at") or ""))
    return deduped


def _load_rebar_live_proofs(
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
    normalized_report_type = _normalize_report_type(report_type)
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

    rows = [x for x in rows if _proof_matches_location(x, location)]
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

        # Strict binding: if current export scope has concrete inspections/proof_ids,
        # only include matching proof_utxo rows to avoid mixing historical records.
        if record_ids or record_proof_ids:
            strict_rows: list[dict[str, Any]] = []
            for row in rows:
                proof_id = str(row.get("proof_id") or "").strip()
                inspection_id = _proof_inspection_id(row)
                if record_proof_ids and proof_id in record_proof_ids:
                    strict_rows.append(row)
                    continue
                if record_ids and inspection_id and inspection_id in record_ids:
                    strict_rows.append(row)

            if strict_rows:
                return _dedupe_proofs_for_export(strict_rows)
            # Fall back to inspection rows below when strict matching returns empty.
            rows = []
        else:
            # Legacy mode: no direct inspection/proof mapping available.
            def _looks_like_business_proof(row: dict[str, Any]) -> bool:
                sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
                return any(
                    sd.get(key) not in (None, "", [])
                    for key in ("value", "values", "type", "type_name", "design", "standard")
                )

            legacy_rows = [x for x in rows if _looks_like_business_proof(x)]
            if legacy_rows:
                return _dedupe_proofs_for_export(legacy_rows)
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
                        "executor_uri": _guess_executor_uri(project_uri_clean, rec.get("person")),
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


def _proof_utxo_row_to_render_proof(row: dict[str, Any], *, report_type: str = "inspection") -> dict[str, Any]:
    """
    Adapt one proof_utxo row into DocxEngine inspection render payload.
    Keeps schema-driven fields in state_data so render_inspection_report can
    auto-handle flatness/rebar/etc.
    """
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


def _project_meta_from_proof_rows(
    sb: Client,
    *,
    rows: list[dict[str, Any]],
    report_type: str,
) -> tuple[dict[str, Any], str | None, str | None]:
    """
    Build render meta from proof rows + projects table.
    Returns: (project_meta, project_id, enterprise_id)
    """
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

    normalized_type = _normalize_report_type(report_type)
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
        "template_name": _template_for_report(normalized_type),
    }
    return project_meta, (str(proj.get("id") or "").strip() or project_id), (str(proj.get("enterprise_id") or "").strip() or None)


def _render_and_upload_rebar_docx(
    sb: Client,
    *,
    proofs: list[dict[str, Any]],
    report_no: str,
    enterprise_id: str,
    project_id: str,
    project_meta: dict[str, Any],
) -> tuple[str, str, str]:
    if not proofs:
        return "", "", ""
    try:
        bytes_data = DocxEngine().render_universal_report(proofs, project_meta, report_type="inspection")
        file_name = f"{report_no}.docx"
        storage_path = f"{enterprise_id}/{project_id}/{file_name}"
        sb.storage.from_(REPORTS_BUCKET).upload(
            storage_path,
            bytes_data,
            file_options={
                "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            },
        )
        file_url = _report_file_url(sb, storage_path, fallback="")
        return storage_path, file_url, str(project_meta.get("template_name") or "01_inspection_report.docx")
    except Exception:
        return "", "", ""


def _render_and_upload_docpeg_docx(
    sb: Client,
    *,
    proofs: list[dict[str, Any]],
    report_no: str,
    enterprise_id: str,
    project_id: str,
    project_meta: dict[str, Any],
    report_type: str,
    output_format: str = "docx",
) -> tuple[str, str, str, str]:
    if not proofs:
        return "", "", "", "docx"
    try:
        normalized_type = _normalize_report_type(report_type)
        template_name = str(project_meta.get("template_name") or _template_for_report(normalized_type))
        project_meta_render = dict(project_meta)
        project_meta_render["template_name"] = template_name
        engine = DocxEngine()
        bytes_data = engine.render_universal_report(
            proofs,
            project_meta_render,
            report_type=normalized_type,
        )
        actual_format = "docx"
        upload_bytes = bytes_data
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if str(output_format or "").strip().lower() == "pdf":
            pdf_bytes = _try_convert_docx_to_pdf(bytes_data)
            if pdf_bytes:
                actual_format = "pdf"
                upload_bytes = pdf_bytes
                content_type = "application/pdf"

        file_name = f"{report_no}.{actual_format}"
        storage_path = f"{enterprise_id}/{project_id}/{file_name}"
        sb.storage.from_(REPORTS_BUCKET).upload(
            storage_path,
            upload_bytes,
            file_options={
                "content-type": content_type
            },
        )
        file_url = _report_file_url(sb, storage_path, fallback="")
        return storage_path, file_url, template_name, actual_format
    except Exception:
        return "", "", "", "docx"


def _report_stats_from_proofs(proofs: list[dict[str, Any]]) -> tuple[int, int, int, int, float]:
    total = len(proofs or [])
    pass_count = 0
    fail_count = 0
    warn_count = 0
    for proof in proofs or []:
        result = _effective_result_from_proof(proof)
        if result == "PASS":
            pass_count += 1
        elif result == "FAIL":
            fail_count += 1
        elif result == "OBSERVE":
            warn_count += 1
    pass_rate = round(pass_count / total * 100, 1) if total else 0
    return total, pass_count, warn_count, fail_count, pass_rate


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        text = str(value or "").strip()
        if not text:
            return None
        m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None
        
        
def _effective_operator(sd: dict[str, Any], *, default: str = "<=") -> str:
    op = str(
        sd.get("standard_op")
        or sd.get("standard_operator")
        or sd.get("operator")
        or sd.get("comparator")
        or sd.get("compare")
        or ""
    ).strip().lower()
    if op in {"+-", "+/-", "\u00b1", "±", "plusminus", "plus_minus"}:
        return "±"
    return op or default


def _compare_values(values: list[float], standard: float, operator: str) -> str:
    op = operator.strip().lower()
    if op in {"<=", "le", "lte", "max", "upper"}:
        return "PASS" if all(v <= standard for v in values) else "FAIL"
    if op in {">=", "ge", "gte", "min", "lower"}:
        return "PASS" if all(v >= standard for v in values) else "FAIL"
    if op in {"=", "==", "eq"}:
        return "PASS" if all(abs(v - standard) < 1e-9 for v in values) else "FAIL"
    # Generic inspection fallback.
    return "PASS" if all(v <= standard for v in values) else "FAIL"


def _parse_limit(limit: Any) -> float | None:
    text = str(limit or "").strip()
    if not text:
        return None
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return abs(float(m.group(0)))
    except Exception:
        return None


def _coerce_values(values_raw: Any, fallback_value: Any = None) -> list[float]:
    values: list[float] = []
    if isinstance(values_raw, list):
        for item in values_raw:
            v = _to_float(item)
            if v is not None:
                values.append(v)
    fb = _to_float(fallback_value)
    if values and fb is not None:
        # Keep in sync with docx_engine: repair legacy [0] placeholder values.
        if len(values) == 1 and abs(values[0]) < 1e-9 and abs(fb) >= 1e-9:
            return [fb]
        return values
    if not values and fb is not None:
        return [fb]
    return values


def _effective_result_from_proof(proof: dict[str, Any]) -> str:
    sd = proof.get("state_data") if isinstance(proof.get("state_data"), dict) else {}
    values = _coerce_values(sd.get("values"), fallback_value=sd.get("value"))
    spec_uri = specir_derive_spec_uri(
        sd,
        row_norm_uri=proof.get("norm_uri"),
        fallback_norm_ref=sd.get("norm_ref"),
    )
    resolved = specir_resolve_spec_rule(
        spec_uri=spec_uri,
        metric=sd.get("type_name") or sd.get("test_name") or sd.get("type"),
        test_type=sd.get("type") or sd.get("test_type"),
        test_name=sd.get("type_name") or sd.get("test_name"),
        context={
            "component_type": sd.get("component_type") or sd.get("structure_type"),
            "stake": sd.get("stake") or sd.get("location"),
        },
        sb=None,
    )
    op = str(resolved.get("operator") or _effective_operator(sd)).strip()
    threshold = resolved.get("threshold")
    if threshold is None:
        threshold = _to_float(sd.get("standard_value"))
    if threshold is None:
        threshold = _to_float(sd.get("standard"))
    if threshold is None:
        threshold = _to_float(sd.get("design"))
    tolerance = resolved.get("tolerance")
    if tolerance is None:
        tolerance = _parse_limit(sd.get("standard_tolerance"))
    if tolerance is None:
        tolerance = _parse_limit(sd.get("tolerance"))
    if tolerance is None:
        tolerance = _parse_limit(sd.get("limit"))
    evaluated = specir_evaluate_measurements(
        values=values,
        operator=op,
        threshold=_to_float(threshold),
        tolerance=_to_float(tolerance),
        fallback_result=proof.get("result") or "PENDING",
    )
    return str(evaluated.get("result") or proof.get("result") or "PENDING").upper()


def _conclusion_from_counts(*, pass_count: int, warn_count: int, fail_count: int) -> str:
    if fail_count == 0 and warn_count == 0:
        return "全部合格：本次检测所有项目均符合规范要求"
    if fail_count == 0:
        return f"基本合格：{warn_count}项需持续观察"
    return f"存在不合格项：{fail_count}项不合格，需整改后复测"


def _try_convert_docx_to_pdf(docx_bytes: bytes) -> bytes | None:
    """
    Best-effort conversion via LibreOffice (soffice). Returns None when unavailable.
    """
    soffice = shutil.which("soffice")
    if not soffice:
        return None
    try:
        with tempfile.TemporaryDirectory(prefix="docpeg_pdf_") as td:
            tmp_dir = Path(td)
            in_docx = tmp_dir / "report.docx"
            out_pdf = tmp_dir / "report.pdf"
            in_docx.write_bytes(docx_bytes)
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(tmp_dir), str(in_docx)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if out_pdf.exists():
                return out_pdf.read_bytes()
    except Exception:
        return None
    return None


def _generate_report_task(
    project_id: str,
    ent_id: str,
    location: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    supabase_url: str,
    supabase_key: str,
):
    """Background task: aggregate data and create report row + proof record."""
    try:
        sb = _supabase_client_cached(str(supabase_url or "").strip(), str(supabase_key or "").strip())
        inspected_from = _normalize_dt(date_from, end_of_day=False)
        inspected_to = _normalize_dt(date_to, end_of_day=True)

        # Load inspections in range/location
        q = sb.table("inspections").select("*").eq("project_id", project_id)
        if location:
            q = q.eq("location", location)
        if inspected_from:
            q = q.gte("inspected_at", inspected_from)
        if inspected_to:
            q = q.lte("inspected_at", inspected_to)
        records = q.execute().data or []

        # Load photos in range/location
        pq = sb.table("photos").select("*").eq("project_id", project_id)
        if location:
            pq = pq.eq("location", location)
        if inspected_from:
            pq = pq.gte("taken_at", inspected_from)
        if inspected_to:
            pq = pq.lte("taken_at", inspected_to)
        photos = pq.execute().data or []

        # Load project
        proj = (
            sb.table("projects")
            .select("v_uri, name, contract_no, supervisor")
            .eq("id", project_id)
            .single()
            .execute()
            .data
        )
        if not proj:
            return

        total = len(records)
        passed = sum(1 for r in records if r.get("result") == "pass")
        warned = sum(1 for r in records if r.get("result") == "warn")
        failed = sum(1 for r in records if r.get("result") == "fail")
        rate = round(passed / total * 100, 1) if total else 0

        now = datetime.utcnow()
        report_no = f"QC-{now.strftime('%Y%m%d%H%M%S')}"
        report_uri = f"{proj['v_uri']}reports/{report_no}/"
        proof_id = _gen_proof(report_uri, {"total": total, "pass_rate": rate})

        if failed == 0 and warned == 0:
            conclusion = "全部合格：本次检测所有项目均符合规范要求"
        elif failed == 0:
            conclusion = f"基本合格：{warned}项需持续观察"
        else:
            conclusion = f"存在不合格项：{failed}项不合格，需整改后复测"

        fail_items = "；".join(
            f"{r.get('type_name', r.get('type', ''))}（{r.get('location', '-') }）"
            for r in records
            if r.get("result") == "fail"
        ) or "无"

        report_proofs = _load_rebar_live_proofs(
            sb,
            project_uri=str(proj.get("v_uri") or ""),
            records=records,
            location=location,
            inspected_from=inspected_from,
            inspected_to=inspected_to,
            proof_types=["inspection"],
            report_type="inspection",
        )
        report_proofs = _filter_inspection_template_proofs(report_proofs)
        total, passed, warned, failed, rate = _report_stats_from_proofs(report_proofs)
        conclusion = _conclusion_from_counts(pass_count=passed, warn_count=warned, fail_count=failed)
        fail_items = "；".join(
            f"{((p.get('state_data') or {}).get('type_name') or (p.get('state_data') or {}).get('type') or '')}"
            f"（{((p.get('state_data') or {}).get('location') or '-') }）"
            for p in report_proofs
            if _effective_result_from_proof(p) == "FAIL"
        ) or "无"
        report_meta = {
            "name": proj.get("name"),
            "project_name": proj.get("name"),
            "project_uri": proj.get("v_uri"),
            "contract_no": proj.get("contract_no"),
            "stake_range": location or "-",
            "check_date": now.strftime("%Y-%m-%d"),
            "inspector": "系统自动生成",
            "tech_leader": proj.get("supervisor") or "-",
            "template_name": "01_inspection_report.docx",
        }
        file_path, file_url, template_used = _render_and_upload_rebar_docx(
            sb,
            proofs=report_proofs,
            report_no=report_no,
            enterprise_id=ent_id,
            project_id=project_id,
            project_meta=report_meta,
        )

        report_payload = {
            "project_id": project_id,
            "enterprise_id": ent_id,
            "v_uri": report_uri,
            "report_no": report_no,
            "location": location,
            # Compatible with mixed schemas: removed automatically if column absent.
            "date_from": inspected_from,
            "date_to": inspected_to,
            "total_count": total,
            "pass_count": passed,
            "warn_count": warned,
            "fail_count": failed,
            "pass_rate": rate,
            "conclusion": conclusion,
            "fail_items": fail_items,
            "file_path": file_path or None,
            "file_url": file_url or None,
            "template_used": template_used or None,
            "proof_id": proof_id,
            "proof_status": "confirmed",
            "inspection_ids": [r.get("id") for r in records if r.get("id")],
            "photo_ids": [p.get("id") for p in photos if p.get("id")],
        }
        _insert_report_compat(sb, report_payload)

        sb.table("proof_chain").insert(
            {
                "proof_id": proof_id,
                "proof_hash": proof_id.replace("GP-PROOF-", "").lower(),
                "enterprise_id": ent_id,
                "project_id": project_id,
                "v_uri": report_uri,
                "object_type": "report",
                "action": "generate",
                "summary": f"报告生成·{report_no}·合格率{rate}%",
                "status": "confirmed",
            }
        ).execute()

        try:
            latest_sign = {}
            if report_proofs:
                signed_by = report_proofs[-1].get("signed_by") if isinstance(report_proofs[-1].get("signed_by"), list) else []
                if signed_by and isinstance(signed_by[0], dict):
                    latest_sign = signed_by[0]
            signer_uri = str(latest_sign.get("executor_uri") or _guess_owner_uri(proj.get("v_uri")))
            ProofUTXOEngine(sb).create(
                proof_id=proof_id,
                owner_uri=_guess_owner_uri(proj.get("v_uri")),
                project_id=project_id,
                project_uri=str(proj.get("v_uri") or report_uri),
                proof_type="archive",
                result="PASS",
                state_data={
                    "report_no": report_no,
                    "report_uri": report_uri,
                    "location": location,
                    "total_count": total,
                    "pass_count": passed,
                    "warn_count": warned,
                    "fail_count": failed,
                    "pass_rate": rate,
                    "file_path": file_path,
                    "file_url": file_url,
                    "template_used": template_used,
                    "inspection_ids": [r.get("id") for r in records if r.get("id")],
                    "photo_ids": [p.get("id") for p in photos if p.get("id")],
                    "source_proof_ids": [str(p.get("proof_id") or "") for p in report_proofs if p.get("proof_id")],
                },
                signer_uri=signer_uri,
                signer_role="AI",
                conditions=[],
                parent_proof_id=None,
                norm_uri=None,
            )
        except Exception:
            # Keep report generation non-blocking if proof_utxo is unavailable.
            pass

        print(f"[reports] generated: {report_no} {report_uri}")
    except Exception as exc:
        print(f"[reports] generate failed project_id={project_id}: {exc}")
        traceback.print_exc()


@router.post("/export")
async def export_report(
    body: ReportExportRequest,
    sb: Client = Depends(get_supabase),
):
    """
    Synchronous DocPeg export endpoint.
    """
    report_type = _normalize_report_type(body.type)
    requested_format = str(body.format or "docx").strip().lower()
    if requested_format not in {"docx", "pdf"}:
        raise HTTPException(400, "format must be docx or pdf")
    inspected_from = _normalize_dt(body.date_from, end_of_day=False)
    inspected_to = _normalize_dt(body.date_to, end_of_day=True)

    proj_res = (
        sb.table("projects")
        .select("id, v_uri, name, contract_no, supervisor")
        .eq("id", body.project_id)
        .eq("enterprise_id", body.enterprise_id)
        .limit(1)
        .execute()
    )
    if not proj_res.data:
        raise HTTPException(404, "project not found for current enterprise")
    proj = proj_res.data[0]
    project_uri = str(proj.get("v_uri") or "").strip()
    if not project_uri:
        raise HTTPException(400, "project v_uri is required")

    records: list[dict[str, Any]] = []
    if report_type in {"inspection", "monthly_summary", "final_archive"}:
        q = sb.table("inspections").select("*").eq("project_id", body.project_id)
        if body.location:
            q = q.eq("location", body.location)
        if inspected_from:
            q = q.gte("inspected_at", inspected_from)
        if inspected_to:
            q = q.lte("inspected_at", inspected_to)
        records = q.execute().data or []

    proof_types = _proof_types_for_report(report_type)
    proofs = _load_rebar_live_proofs(
        sb,
        project_uri=project_uri,
        records=records,
        location=body.location,
        inspected_from=inspected_from,
        inspected_to=inspected_to,
        proof_types=proof_types,
        report_type=report_type,
    )
    if report_type == "inspection":
        proofs = _filter_inspection_template_proofs(proofs)
    if not proofs:
        raise HTTPException(404, "no source proofs found for this export scope")

    now = datetime.utcnow()
    report_prefix = {
        "inspection": "QC",
        "lab": "LAB",
        "monthly_summary": "MON",
        "final_archive": "ARC",
    }.get(report_type, "DOCPEG")
    report_no = f"{report_prefix}-{now.strftime('%Y%m%d%H%M%S')}"
    report_uri = f"{project_uri}reports/{report_no}/"

    total, passed, warned, failed, rate = _report_stats_from_proofs(proofs)
    conclusion = _conclusion_from_counts(pass_count=passed, warn_count=warned, fail_count=failed)
    fail_items = "；".join(
        f"{((p.get('state_data') or {}).get('type_name') or (p.get('state_data') or {}).get('type') or '')}"
        f"（{((p.get('state_data') or {}).get('location') or '-') }）"
        for p in proofs
        if _effective_result_from_proof(p) == "FAIL"
    ) or "无"

    template_name = _template_for_report(report_type)
    report_meta = {
        "name": proj.get("name"),
        "project_name": proj.get("name"),
        "project_uri": project_uri,
        "contract_no": proj.get("contract_no"),
        "stake_range": body.location or "-",
        "check_date": now.strftime("%Y-%m-%d"),
        "inspector": "系统自动生成",
        "tech_leader": proj.get("supervisor") or "-",
        "template_name": template_name,
    }
    file_path, file_url, template_used, output_format = _render_and_upload_docpeg_docx(
        sb,
        proofs=proofs,
        report_no=report_no,
        enterprise_id=body.enterprise_id,
        project_id=body.project_id,
        project_meta=report_meta,
        report_type=report_type,
        output_format=requested_format,
    )
    if not file_url:
        raise HTTPException(500, "docx export failed")

    proof_id = _gen_proof(
        report_uri,
        {"total": total, "pass_rate": rate, "report_type": report_type, "template": template_used},
    )
    report_payload = {
        "project_id": body.project_id,
        "enterprise_id": body.enterprise_id,
        "v_uri": report_uri,
        "report_no": report_no,
        "location": body.location,
        "date_from": inspected_from,
        "date_to": inspected_to,
        "total_count": total,
        "pass_count": passed,
        "warn_count": warned,
        "fail_count": failed,
        "pass_rate": rate,
        "conclusion": conclusion,
        "fail_items": fail_items,
        "file_path": file_path or None,
        "file_url": file_url or None,
        "template_used": template_used or None,
        "report_type": report_type,
        "report_format": output_format,
        "proof_id": proof_id,
        "proof_status": "confirmed",
        "inspection_ids": [r.get("id") for r in records if r.get("id")],
    }
    _insert_report_compat(sb, report_payload)

    sb.table("proof_chain").insert(
        {
            "proof_id": proof_id,
            "proof_hash": proof_id.replace("GP-PROOF-", "").lower(),
            "enterprise_id": body.enterprise_id,
            "project_id": body.project_id,
            "v_uri": report_uri,
            "object_type": "report",
            "action": "export",
            "summary": f"DocPeg导出·{report_no}·合格率{rate}%",
            "status": "confirmed",
        }
    ).execute()

    latest_sign = {}
    if proofs:
        signed_by = proofs[-1].get("signed_by") if isinstance(proofs[-1].get("signed_by"), list) else []
        if signed_by and isinstance(signed_by[0], dict):
            latest_sign = signed_by[0]
    signer_uri = str(latest_sign.get("executor_uri") or _guess_owner_uri(project_uri))

    utxo = ProofUTXOEngine(sb).create(
        proof_id=proof_id,
        owner_uri=_guess_owner_uri(project_uri),
        project_id=body.project_id,
        project_uri=project_uri,
        proof_type="archive",
        result="PASS" if failed == 0 else "OBSERVE",
        state_data={
            "report_type": report_type,
            "report_no": report_no,
            "report_uri": report_uri,
            "location": body.location,
            "total_count": total,
            "pass_count": passed,
            "warn_count": warned,
            "fail_count": failed,
            "pass_rate": rate,
            "file_path": file_path,
            "file_url": file_url,
            "template_used": template_used,
            "report_format": output_format,
            "source_proof_ids": [str(p.get("proof_id") or "") for p in proofs if p.get("proof_id")],
        },
        signer_uri=signer_uri,
        signer_role="AI",
        conditions=[],
        parent_proof_id=None,
        norm_uri=None,
    )

    return {
        "ok": True,
        "report_type": report_type,
        "report_no": report_no,
        "template_used": template_used,
        "requested_format": requested_format,
        "output_format": output_format,
        "file_url": file_url,
        "proof_id": proof_id,
        "proof_hash": utxo.get("proof_hash") if isinstance(utxo, dict) else None,
        "gitpeg_anchor": utxo.get("gitpeg_anchor") if isinstance(utxo, dict) else None,
        "counts": {
            "total": total,
            "pass": passed,
            "warn": warned,
            "fail": failed,
            "pass_rate": rate,
        },
    }


@router.get("/export")
async def export_report_by_proof_id(
    proof_id: str = Query(..., description="Proof UTXO ID, e.g. GP-PROOF-XXXX"),
    format: str = Query("docx", regex="^(docx|pdf)$"),
    report_type: str = Query("inspection"),
    sb: Client = Depends(get_supabase),
):
    """
    Real-time report export by proof_id.
    This route is available under both:
    - /v1/reports/export?proof_id=...
    - /api/reports/export?proof_id=...
    """
    normalized_type = _normalize_report_type(report_type)
    row = ProofUTXOEngine(sb).get_by_id(str(proof_id).strip())
    if not isinstance(row, dict):
        raise HTTPException(404, "proof_utxo not found")

    source_report_type = str(row.get("proof_type") or normalized_type).strip().lower()
    effective_type = normalized_type if normalized_type != "inspection" else _normalize_report_type(source_report_type)
    if effective_type not in REPORT_TEMPLATE_BY_TYPE:
        effective_type = "inspection"

    proofs = [_proof_utxo_row_to_render_proof(row, report_type=effective_type)]
    project_meta, project_id, _enterprise_id = _project_meta_from_proof_rows(
        sb,
        rows=proofs,
        report_type=effective_type,
    )
    if not project_meta.get("project_uri"):
        # Keep sovereignty completeness at least from proof row.
        project_meta["project_uri"] = str(row.get("project_uri") or "")

    engine = DocxEngine()
    docx_bytes = engine.render_universal_report(
        proofs,
        project_meta,
        report_type=effective_type,
    )

    output_fmt = str(format or "docx").strip().lower()
    payload = docx_bytes
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if output_fmt == "pdf":
        pdf_bytes = _try_convert_docx_to_pdf(docx_bytes)
        if pdf_bytes:
            payload = pdf_bytes
            media_type = "application/pdf"
        else:
            output_fmt = "docx"

    pid = str(project_id or row.get("project_id") or "project")
    download_name = f"{pid}_{str(proof_id).strip()}.{output_fmt}"
    headers = {"Content-Disposition": f'attachment; filename="{download_name}"'}
    return StreamingResponse(io.BytesIO(payload), media_type=media_type, headers=headers)


@router.post("/generate", status_code=202)
async def generate_report(
    body: ReportRequest,
    background_tasks: BackgroundTasks,
    sb: Client = Depends(get_supabase),
):
    """Trigger async report generation."""
    # Make sure project exists and belongs to enterprise before enqueue.
    proj = (
        sb.table("projects")
        .select("id")
        .eq("id", body.project_id)
        .eq("enterprise_id", body.enterprise_id)
        .limit(1)
        .execute()
    )
    if not proj.data:
        raise HTTPException(404, "project not found for current enterprise")

    background_tasks.add_task(
        _generate_report_task,
        body.project_id,
        body.enterprise_id,
        body.location,
        body.date_from,
        body.date_to,
        str(os.getenv("SUPABASE_URL") or ""),
        str(
            os.getenv("SUPABASE_SERVICE_KEY")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or ""
        ),
    )
    return {"accepted": True, "message": "报告生成中，请稍后查询"}


@router.get("/")
async def list_reports(
    project_id: str,
    sb: Client = Depends(get_supabase),
):
    res = (
        sb.table("reports")
        .select("*")
        .eq("project_id", project_id)
        .order("generated_at", desc=True)
        .execute()
    )
    rows = res.data or []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        item["file_url"] = _report_file_url(
            sb,
            str(item.get("file_path") or ""),
            fallback=str(item.get("file_url") or ""),
        )
        normalized.append(item)
    return {"data": normalized}


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    sb: Client = Depends(get_supabase),
):
    res = sb.table("reports").select("*").eq("id", report_id).single().execute()
    if not res.data:
        raise HTTPException(404, "报告不存在")
    row = dict(res.data)
    row["file_url"] = _report_file_url(
        sb,
        str(row.get("file_path") or ""),
        fallback=str(row.get("file_url") or ""),
    )
    return row

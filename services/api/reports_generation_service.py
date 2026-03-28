"""
Report generation service helpers.
services/api/reports_generation_service.py
"""

from __future__ import annotations

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
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException
from postgrest.exceptions import APIError
from supabase import Client

from services.api.docx_engine import DocxEngine
from services.api.reports_eval_service import (
    conclusion_from_counts as _conclusion_from_counts,
    effective_result_from_proof as _effective_result_from_proof,
    report_stats_from_proofs as _report_stats_from_proofs,
)
from services.api.reports_proof_service import (
    REPORT_TEMPLATE_BY_TYPE,
    filter_inspection_template_proofs as _filter_inspection_template_proofs,
    load_rebar_live_proofs as _load_rebar_live_proofs,
    normalize_report_type as _normalize_report_type,
    project_meta_from_proof_rows as _project_meta_from_proof_rows,
    proof_types_for_report as _proof_types_for_report,
    template_for_report as _template_for_report,
)
from services.api.proof_utxo_engine import ProofUTXOEngine

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




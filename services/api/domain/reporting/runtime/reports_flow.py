"""
Flow helpers for reports router endpoints.
"""

from __future__ import annotations

from datetime import datetime
import io
import os
from typing import Any

from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from supabase import Client

from services.api.infrastructure.document.engine import DocxEngine
from services.api.domain.utxo.integrations import ProofUTXOEngine
from services.api.domain.reporting.runtime.reports_eval import (
    conclusion_from_counts as _conclusion_from_counts,
    effective_result_from_proof as _effective_result_from_proof,
    report_stats_from_proofs as _report_stats_from_proofs,
)
from services.api.domain.reporting.runtime.reports_generation import (
    _gen_proof,
    _generate_report_task,
    _guess_owner_uri,
    _insert_report_compat,
    _normalize_dt,
    _render_and_upload_docpeg_docx,
    _report_file_url,
    _try_convert_docx_to_pdf,
)
from services.api.domain.reporting.runtime.reports_proof import (
    REPORT_TEMPLATE_BY_TYPE,
    filter_inspection_template_proofs as _filter_inspection_template_proofs,
    load_rebar_live_proofs as _load_rebar_live_proofs,
    normalize_report_type as _normalize_report_type,
    project_meta_from_proof_rows as _project_meta_from_proof_rows,
    proof_types_for_report as _proof_types_for_report,
    proof_utxo_row_to_render_proof as _proof_utxo_row_to_render_proof,
    template_for_report as _template_for_report,
)


async def export_report_flow(
    *,
    body: Any,
    sb: Client,
) -> dict[str, Any]:
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
    fail_items = "; ".join(
        f"{((p.get('state_data') or {}).get('type_name') or (p.get('state_data') or {}).get('type') or '')}"
        f" ({((p.get('state_data') or {}).get('location') or '-')})"
        for p in proofs
        if _effective_result_from_proof(p) == "FAIL"
    ) or "none"

    template_name = _template_for_report(report_type)
    report_meta = {
        "name": proj.get("name"),
        "project_name": proj.get("name"),
        "project_uri": project_uri,
        "contract_no": proj.get("contract_no"),
        "stake_range": body.location or "-",
        "check_date": now.strftime("%Y-%m-%d"),
        "inspector": "system",
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
            "summary": f"DocPeg export {report_no} pass_rate {rate}%",
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


async def export_report_by_proof_id_flow(
    *,
    proof_id: str,
    format: str,
    report_type: str,
    sb: Client,
) -> StreamingResponse:
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


async def generate_report_flow(
    *,
    body: Any,
    background_tasks: BackgroundTasks,
    sb: Client,
) -> dict[str, Any]:
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
    return {"accepted": True, "message": "report generation accepted"}


def list_reports_flow(*, project_id: str, sb: Client) -> dict[str, Any]:
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


def get_report_flow(*, report_id: str, sb: Client) -> dict[str, Any]:
    res = sb.table("reports").select("*").eq("id", report_id).single().execute()
    if not res.data:
        raise HTTPException(404, "report not found")
    row = dict(res.data)
    row["file_url"] = _report_file_url(
        sb,
        str(row.get("file_path") or ""),
        fallback=str(row.get("file_url") or ""),
    )
    return row

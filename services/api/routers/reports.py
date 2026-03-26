"""
QCSpec report routes
services/api/routers/reports.py
"""

from datetime import datetime
import hashlib
import json
import os
import re
import traceback
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from postgrest.exceptions import APIError
from pydantic import BaseModel
from supabase import Client, create_client

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


def _normalize_dt(raw: Optional[str], end_of_day: bool = False) -> Optional[str]:
    text = str(raw or "").strip()
    if not text:
        return None
    # YYYY-MM-DD -> explicit day boundary
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return f"{text}T23:59:59" if end_of_day else f"{text}T00:00:00"
    return text


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
                    "inspection_ids": [r.get("id") for r in records if r.get("id")],
                    "photo_ids": [p.get("id") for p in photos if p.get("id")],
                },
                signer_uri=_guess_owner_uri(proj.get("v_uri")),
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
    return {"data": res.data}


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    sb: Client = Depends(get_supabase),
):
    res = sb.table("reports").select("*").eq("id", report_id).single().execute()
    if not res.data:
        raise HTTPException(404, "报告不存在")
    return res.data

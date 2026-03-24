"""
QCSpec inspection routes
services/api/routers/inspections.py
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
import hashlib
import json
import os
from functools import lru_cache

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from postgrest.exceptions import APIError
from supabase import Client, create_client

router = APIRouter()

@lru_cache(maxsize=1)
def _supabase_client_cached(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase() -> Client:
    url = str(os.getenv("SUPABASE_URL") or "").strip()
    key = str(os.getenv("SUPABASE_SERVICE_KEY") or "").strip()
    if not url or not key:
        raise HTTPException(500, "Supabase not configured")
    return _supabase_client_cached(url, key)


class InspectionCreate(BaseModel):
    project_id: str
    location: str
    type: str
    type_name: str
    value: float
    standard: Optional[float] = None
    unit: str = ""
    result: str  # pass / warn / fail
    person: Optional[str] = None
    remark: Optional[str] = None
    inspected_at: Optional[str] = None
    photo_ids: Optional[List[str]] = []


class InspectionFilter(BaseModel):
    result: Optional[str] = None
    type: Optional[str] = None
    location: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except Exception:
        return False


def _run_with_retry(fn, retries: int = 1):
    last_err = None
    for _ in range(retries + 1):
        try:
            return fn()
        except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout) as e:
            last_err = e
            continue
    if last_err:
        raise last_err


def _gen_proof(v_uri: str, data: dict) -> str:
    payload = json.dumps(
        {
            "uri": v_uri,
            "data": data,
            "ts": datetime.utcnow().isoformat(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    h = hashlib.sha256(payload.encode()).hexdigest()[:16].upper()
    return f"GP-PROOF-{h}"


@router.get("/")
async def list_inspections(
    project_id: str,
    result: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    sb: Client = Depends(get_supabase),
):
    """List inspections by project."""
    if not _is_uuid(project_id):
        raise HTTPException(400, "Invalid project_id format. UUID expected.")

    def _query():
        q = (
            sb.table("inspections")
            .select("*")
            .eq("project_id", project_id)
            .order("inspected_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if result:
            q = q.eq("result", result)
        if type:
            q = q.eq("type", type)
        return q.execute()

    try:
        res = _run_with_retry(_query, retries=1)
        rows = res.data or []
        return {"data": rows, "count": len(rows)}
    except APIError as e:
        if "invalid input syntax for type uuid" in str(e):
            raise HTTPException(400, "Invalid project_id format. UUID expected.")
        raise HTTPException(502, "Failed to query inspections from database.")
    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        # Avoid breaking the whole page for transient upstream disconnects.
        return {"data": [], "count": 0}


@router.post("/", status_code=201)
async def create_inspection(
    body: InspectionCreate,
    sb: Client = Depends(get_supabase),
):
    """Create an inspection and append proof-chain record."""
    if not _is_uuid(body.project_id):
        raise HTTPException(400, "Invalid project_id format. UUID expected.")

    try:
        proj = _run_with_retry(
            lambda: sb.table("projects")
            .select("v_uri, enterprise_id")
            .eq("id", body.project_id)
            .single()
            .execute(),
            retries=1,
        )
    except APIError as e:
        if "invalid input syntax for type uuid" in str(e):
            raise HTTPException(400, "Invalid project_id format. UUID expected.")
        raise HTTPException(502, "Failed to query project.")
    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        raise HTTPException(503, "Database temporarily unavailable. Please retry.")

    if not proj.data:
        raise HTTPException(404, "Project not found")

    proj_uri = proj.data["v_uri"]
    ent_id = proj.data["enterprise_id"]
    now = body.inspected_at or datetime.utcnow().isoformat()

    rec = {
        "project_id": body.project_id,
        "enterprise_id": ent_id,
        "location": body.location,
        "type": body.type,
        "type_name": body.type_name,
        "value": body.value,
        "standard": body.standard,
        "unit": body.unit,
        "result": body.result,
        "person": body.person,
        "remark": body.remark,
        "inspected_at": now,
    }

    try:
        ins = _run_with_retry(lambda: sb.table("inspections").insert(rec).execute(), retries=1)
    except APIError:
        raise HTTPException(502, "Failed to write inspection.")
    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        raise HTTPException(503, "Database temporarily unavailable. Please retry.")

    if not ins.data:
        raise HTTPException(500, "Failed to write inspection")

    insp = ins.data[0]
    v_uri = insp.get("v_uri") or f"{proj_uri}inspection/{insp['id']}/"

    proof_id = _gen_proof(
        v_uri,
        {
            "value": body.value,
            "result": body.result,
            "location": body.location,
        },
    )

    try:
        _run_with_retry(
            lambda: sb.table("inspections")
            .update({"proof_id": proof_id, "proof_status": "confirmed"})
            .eq("id", insp["id"])
            .execute(),
            retries=1,
        )
    except Exception:
        pass

    try:
        _run_with_retry(
            lambda: sb.table("proof_chain").insert(
                {
                    "proof_id": proof_id,
                    "proof_hash": proof_id.replace("GP-PROOF-", "").lower(),
                    "enterprise_id": ent_id,
                    "project_id": body.project_id,
                    "v_uri": v_uri,
                    "object_type": "inspection",
                    "object_id": insp["id"],
                    "action": "create",
                    "summary": f"质检录入·{body.type_name}·{body.location}·{body.result}",
                    "status": "confirmed",
                }
            ).execute(),
            retries=1,
        )
    except Exception:
        pass

    linked_photo_count = 0
    photo_ids = [pid for pid in (body.photo_ids or []) if _is_uuid(pid)]
    if photo_ids:
        try:
            linked = _run_with_retry(
                lambda: sb.table("photos")
                .update({"inspection_id": insp["id"]})
                .eq("project_id", body.project_id)
                .in_("id", photo_ids)
                .execute(),
                retries=1,
            )
            linked_photo_count = len(linked.data or [])
        except Exception:
            linked_photo_count = 0

    return {
        "inspection_id": insp["id"],
        "v_uri": v_uri,
        "proof_id": proof_id,
        "result": body.result,
        "linked_photo_count": linked_photo_count,
    }


@router.get("/stats/{project_id}")
async def project_stats(
    project_id: str,
    sb: Client = Depends(get_supabase),
):
    """Inspection stats for a project."""
    if not _is_uuid(project_id):
        raise HTTPException(400, "Invalid project_id format. UUID expected.")

    try:
        res = _run_with_retry(
            lambda: sb.table("inspections").select("result").eq("project_id", project_id).execute(),
            retries=1,
        )
        rows = res.data or []
    except APIError as e:
        if "invalid input syntax for type uuid" in str(e):
            raise HTTPException(400, "Invalid project_id format. UUID expected.")
        rows = []
    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
        rows = []

    total = len(rows)
    passed = sum(1 for r in rows if r["result"] == "pass")
    warned = sum(1 for r in rows if r["result"] == "warn")
    failed = sum(1 for r in rows if r["result"] == "fail")

    return {
        "total": total,
        "pass": passed,
        "warn": warned,
        "fail": failed,
        "pass_rate": round(passed / total * 100, 1) if total else 0,
    }


@router.delete("/{inspection_id}")
async def delete_inspection(
    inspection_id: str,
    sb: Client = Depends(get_supabase),
):
    """Delete inspection."""
    sb.table("inspections").delete().eq("id", inspection_id).execute()
    return {"ok": True}

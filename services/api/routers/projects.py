"""
QCSpec project routes.
services/api/routers/projects.py
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Optional
from supabase import create_client, Client
from functools import lru_cache
import csv
import json
import os
import re
from io import StringIO
from urllib.parse import quote

import httpx

from .autoreg import AutoRegisterProjectRequest, _normalize_request, _upsert_autoreg

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

def slugify(name: str) -> str:
    """Project name -> stable v:// slug segment."""
    raw = str(name or "").strip().lower()
    compact = re.sub(r"\s+", "", raw, flags=re.UNICODE)
    return re.sub(r"[^\w-]+", "", compact, flags=re.UNICODE)[:20] or "project"


def _normalize_activity_summary(summary: Any, object_type: str, action: str) -> str:
    text = str(summary or "").strip()
    if not text:
        return f"{object_type or 'object'} {action or 'update'}"

    # 历史数据中曾用 "?" 代表未填桩号，这里统一替换成可读文案。
    if object_type == "photo" and action == "upload":
        text = re.sub(r"(照片上传\s*[·•]\s*)\?(\s*[·•])", r"\1未知桩号\2", text)
    return text

class ProjectCreate(BaseModel):
    name:          str
    type:          str
    owner_unit:    str
    contractor:    Optional[str] = None
    supervisor:    Optional[str] = None
    contract_no:   Optional[str] = None
    start_date:    Optional[str] = None
    end_date:      Optional[str] = None
    description:   Optional[str] = None
    seg_type:      str = 'km'
    seg_start:     Optional[str] = None
    seg_end:       Optional[str] = None
    perm_template: str = 'standard'
    enterprise_id: str


class ProjectAutoregSyncRequest(BaseModel):
    enterprise_id: Optional[str] = None
    force: bool = True
    writeback: bool = True


def _load_enterprise(sb: Client, enterprise_id: str) -> dict[str, Any]:
    ent = sb.table("enterprises").select("id,v_uri,name").eq("id", enterprise_id).single().execute()
    if not ent.data:
        raise HTTPException(404, "enterprise not found")
    return ent.data


def _load_sync_custom(sb: Client, enterprise_id: str) -> dict[str, Any]:
    cfg = (
        sb.table("enterprise_configs")
        .select("custom_fields")
        .eq("enterprise_id", enterprise_id)
        .limit(1)
        .execute()
    )
    if not cfg.data:
        return {}
    custom = cfg.data[0].get("custom_fields") or {}
    return custom if isinstance(custom, dict) else {}


def _autoreg_enabled(custom: dict[str, Any]) -> bool:
    return bool(custom.get("erpnext_sync") or custom.get("gitpeg_enabled"))


def _build_autoreg_input(project: dict[str, Any], enterprise: dict[str, Any]) -> AutoRegisterProjectRequest:
    project_name = str(project.get("name") or "").strip()
    project_code = str(project.get("contract_no") or "").strip() or str(project.get("id") or "").strip()
    site_code = slugify(project_name)
    site_name = project_name
    namespace_uri = str(enterprise.get("v_uri") or "").strip() or None
    return AutoRegisterProjectRequest(
        project_code=project_code,
        project_name=project_name,
        site_code=site_code,
        site_name=site_name,
        namespace_uri=namespace_uri,
        source_system="qcspec",
    )


def _erp_headers(site_name: Optional[str], auth_header: Optional[str]) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "QCSpec-Project-Autoreg/1.0",
    }
    site = str(site_name or "").strip()
    if site:
        headers["Host"] = site
        headers["X-Forwarded-Host"] = site
        headers["X-Frappe-Site-Name"] = site
    if auth_header:
        headers["Authorization"] = auth_header
    return headers


def _erp_auth_candidates(api_key: Optional[str], api_secret: Optional[str]) -> list[tuple[str, str]]:
    key = str(api_key or "").strip()
    secret = str(api_secret or "").strip()
    out: list[tuple[str, str]] = []
    if key and secret:
        out.append(("token", f"token {key}:{secret}"))
    elif key:
        lower = key.lower()
        if lower.startswith("token "):
            out.append(("token", key))
        elif lower.startswith("bearer "):
            out.append(("bearer", key))
        elif ":" in key:
            out.append(("token", f"token {key}"))
        else:
            out.append(("bearer", f"Bearer {key}"))
    return out


async def _erp_lookup_docname(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    doctype: str,
    lookup_field: str,
    lookup_value: str,
) -> Optional[str]:
    if lookup_field == "name":
        return lookup_value
    params = {
        "fields": json.dumps(["name"], ensure_ascii=False),
        "filters": json.dumps([[doctype, lookup_field, "=", lookup_value]], ensure_ascii=False),
        "limit_page_length": "1",
    }
    list_url = f"{base_url}/api/resource/{quote(doctype, safe='')}"
    res = await client.get(list_url, headers=headers, params=params)
    if res.status_code >= 400:
        return None
    payload = res.json() if res.content else {}
    rows = payload.get("data") if isinstance(payload, dict) else []
    if not isinstance(rows, list) or not rows:
        return None
    name = rows[0].get("name") if isinstance(rows[0], dict) else None
    return str(name or "").strip() or None


async def _erp_writeback_autoreg(
    custom: dict[str, Any],
    project: dict[str, Any],
    autoreg_response: dict[str, Any],
) -> dict[str, Any]:
    base_url = str(custom.get("erpnext_url") or "").strip().rstrip("/")
    if not base_url:
        return {"attempted": False, "success": False, "reason": "erpnext_url_not_configured"}

    candidates = _erp_auth_candidates(custom.get("erpnext_api_key"), custom.get("erpnext_api_secret"))
    if not candidates:
        return {"attempted": False, "success": False, "reason": "erpnext_api_credentials_not_configured"}

    doctype = str(custom.get("erpnext_project_doctype") or "Project").strip() or "Project"
    lookup_field = str(custom.get("erpnext_project_lookup_field") or "name").strip() or "name"
    lookup_values: list[str] = []
    for candidate in (
        custom.get("erpnext_project_lookup_value"),
        project.get("contract_no"),
        autoreg_response.get("project_code"),
        project.get("name"),
    ):
        value = str(candidate or "").strip()
        if value and value not in lookup_values:
            lookup_values.append(value)
    if not lookup_values:
        return {"attempted": True, "success": False, "reason": "erpnext_lookup_value_missing"}

    f_project_uri = str(custom.get("erpnext_gitpeg_project_uri_field") or "gitpeg_project_uri").strip()
    f_site_uri = str(custom.get("erpnext_gitpeg_site_uri_field") or "gitpeg_site_uri").strip()
    f_status = str(custom.get("erpnext_gitpeg_status_field") or "gitpeg_status").strip()
    f_result_json = str(custom.get("erpnext_gitpeg_result_json_field") or "gitpeg_register_result_json").strip()
    site_name = str(custom.get("erpnext_site_name") or "").strip() or None

    update_doc = {
        f_project_uri: autoreg_response.get("gitpeg_project_uri"),
        f_site_uri: autoreg_response.get("gitpeg_site_uri"),
        f_status: autoreg_response.get("gitpeg_status") or "active",
        f_result_json: json.dumps(autoreg_response, ensure_ascii=False),
    }

    errors: list[str] = []
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for lookup_value in lookup_values:
            for mode, auth_header in candidates:
                headers = _erp_headers(site_name, auth_header)
                try:
                    docname = await _erp_lookup_docname(
                        client=client,
                        base_url=base_url,
                        headers=headers,
                        doctype=doctype,
                        lookup_field=lookup_field,
                        lookup_value=lookup_value,
                    )
                    if not docname:
                        errors.append(f"{mode}:{lookup_field}={lookup_value}:doc_not_found")
                        continue

                    update_url = f"{base_url}/api/resource/{quote(doctype, safe='')}/{quote(docname, safe='')}"
                    res = await client.put(update_url, headers=headers, json=update_doc)
                    if res.status_code >= 400:
                        errors.append(f"{mode}:{lookup_field}={lookup_value}:{res.status_code}")
                        continue
                    return {
                        "attempted": True,
                        "success": True,
                        "authMode": mode,
                        "doctype": doctype,
                        "docname": docname,
                        "lookupField": lookup_field,
                        "lookupValue": lookup_value,
                    }
                except Exception as exc:
                    errors.append(f"{mode}:{lookup_field}={lookup_value}:{exc}")

    return {"attempted": True, "success": False, "errors": errors}


async def _sync_project_autoreg(
    sb: Client,
    project: dict[str, Any],
    *,
    force: bool = False,
    writeback: bool = True,
) -> dict[str, Any]:
    enterprise_id = str(project.get("enterprise_id") or "").strip()
    if not enterprise_id:
        return {"enabled": False, "success": False, "reason": "project_enterprise_id_missing"}

    custom = _load_sync_custom(sb, enterprise_id)
    enabled = _autoreg_enabled(custom)
    if not enabled and not force:
        return {"enabled": False, "success": True, "skipped": True, "reason": "autoreg_disabled"}

    enterprise = _load_enterprise(sb, enterprise_id)
    req = _build_autoreg_input(project, enterprise)
    normalized = _normalize_request(req)
    upsert_info = _upsert_autoreg(sb, normalized)

    autoreg_response = {
        "project_code": normalized["project_code"],
        "project_name": normalized["project_name"],
        "site_code": normalized["site_code"],
        "site_name": normalized["site_name"],
        "gitpeg_project_uri": normalized["project_uri"],
        "gitpeg_site_uri": normalized["site_uri"],
        "gitpeg_executor_uri": normalized["executor_uri"],
        "gitpeg_status": "active",
        "source_system": normalized["source_system"],
        "sync": upsert_info,
    }

    result = {
        "enabled": True,
        "success": True,
        "autoreg": autoreg_response,
    }
    if writeback:
        writeback_res = await _erp_writeback_autoreg(custom, project, autoreg_response)
        result["erp_writeback"] = writeback_res
        if writeback_res.get("attempted") and not writeback_res.get("success"):
            result["success"] = False
    return result

@router.get("/")
async def list_projects(
    enterprise_id: str,
    status: Optional[str] = None,
    type:   Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    q = sb.table("projects").select("*")\
          .eq("enterprise_id", enterprise_id)\
          .order("created_at", desc=True)
    if status: q = q.eq("status", status)
    if type:   q = q.eq("type", type)
    res = q.execute()
    return {"data": res.data}


@router.get("/activity")
async def list_activity(
    enterprise_id: str,
    limit: int = 20,
    sb: Client = Depends(get_supabase),
):
    rows = sb.table("proof_chain").select("proof_id,object_type,action,summary,created_at,project_id")\
             .eq("enterprise_id", enterprise_id)\
             .order("created_at", desc=True)\
             .limit(max(1, min(limit, 100))).execute()
    data = rows.data or []

    dot_by_action = {
        "create": "#1A56DB",
        "submit": "#1A56DB",
        "upload": "#059669",
        "generate": "#D97706",
        "verify": "#0EA5E9",
        "warn": "#DC2626",
    }
    dot_by_type = {
        "inspection": "#1A56DB",
        "photo": "#059669",
        "report": "#D97706",
    }

    items = []
    for row in data:
        action = str(row.get("action") or "").lower()
        obj = str(row.get("object_type") or "").lower()
        dot = dot_by_action.get(action) or dot_by_type.get(obj) or "#64748B"
        summary = _normalize_activity_summary(row.get("summary"), obj, action)
        items.append({
            "dot": dot,
            "text": summary,
            "created_at": row.get("created_at"),
            "proof_id": row.get("proof_id"),
            "project_id": row.get("project_id"),
        })

    return {"data": items}


@router.get("/export")
async def export_projects_csv(
    enterprise_id: str,
    status: Optional[str] = None,
    type: Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    q = sb.table("projects").select("*")\
          .eq("enterprise_id", enterprise_id)\
          .order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    if type:
        q = q.eq("type", type)
    rows = q.execute().data or []

    headers = [
        "id", "name", "type", "status", "owner_unit", "contractor", "supervisor",
        "contract_no", "start_date", "end_date", "v_uri",
        "record_count", "photo_count", "proof_count",
    ]

    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k) for k in headers})
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="projects.csv"',
        },
    )

@router.post("/", status_code=201)
async def create_project(
    body: ProjectCreate,
    sb:   Client = Depends(get_supabase),
):
    enterprise = _load_enterprise(sb, body.enterprise_id)
    root_uri = str(enterprise.get("v_uri") or "").strip() or "v://cn.enterprise/"
    if not root_uri.endswith("/"):
        root_uri += "/"

    # Generate v:// URI
    slug = slugify(body.name)
    v_uri = f"{root_uri}{body.type}/{slug}/"

    # Check duplicate v:// node.
    exist = sb.table("projects").select("id")\
               .eq("v_uri", v_uri).execute()
    if exist.data:
        raise HTTPException(409, f"node already exists: {v_uri}")

    rec = {
        "enterprise_id": body.enterprise_id,
        "v_uri":         v_uri,
        "name":          body.name,
        "type":          body.type,
        "owner_unit":    body.owner_unit,
        "contractor":    body.contractor,
        "supervisor":    body.supervisor,
        "contract_no":   body.contract_no,
        "start_date":    body.start_date,
        "end_date":      body.end_date,
        "description":   body.description,
        "seg_type":      body.seg_type,
        "seg_start":     body.seg_start,
        "seg_end":       body.seg_end,
        "perm_template": body.perm_template,
        "status":        "active",
    }
    res = sb.table("projects").insert(rec).execute()
    if not res.data:
        raise HTTPException(500, "failed to create project")

    proj = res.data[0]
    try:
        sync_result = await _sync_project_autoreg(
            sb,
            proj,
            force=False,
            writeback=True,
        )
    except Exception as exc:
        sync_result = {
            "enabled": True,
            "success": False,
            "reason": f"autoreg_sync_failed: {exc}",
        }
    return {
        "id":    proj["id"],
        "v_uri": proj["v_uri"],
        "name":  proj["name"],
        "autoreg_sync": sync_result,
    }

@router.post("/{project_id}/autoreg-sync")
async def sync_project_autoreg(
    project_id: str,
    body: Optional[ProjectAutoregSyncRequest] = None,
    sb: Client = Depends(get_supabase),
):
    req = body or ProjectAutoregSyncRequest()
    q = sb.table("projects").select("*").eq("id", project_id)
    if req.enterprise_id:
        q = q.eq("enterprise_id", req.enterprise_id)
    row = q.limit(1).execute()
    if not row.data:
        raise HTTPException(404, "project not found")

    result = await _sync_project_autoreg(
        sb,
        row.data[0],
        force=req.force,
        writeback=req.writeback,
    )
    return {
        "ok": bool(result.get("success")),
        "project_id": project_id,
        "result": result,
    }


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    sb: Client = Depends(get_supabase),
):
    res = sb.table("projects").select("*").eq("id", project_id).single().execute()
    if not res.data:
        raise HTTPException(404, "project not found")
    return res.data

@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    updates: dict,
    sb: Client = Depends(get_supabase),
):
    res = sb.table("projects").update(updates).eq("id", project_id).execute()
    return res.data[0] if res.data else {}


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    enterprise_id: Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    check = sb.table("projects").select("id").eq("id", project_id)
    if enterprise_id:
        check = check.eq("enterprise_id", enterprise_id)
    exists = check.limit(1).execute()
    if not exists.data:
        raise HTTPException(404, "project not found")

    # proof_chain.project_id -> projects.id is not ON DELETE CASCADE.
    sb.table("proof_chain").delete().eq("project_id", project_id).execute()

    q = sb.table("projects").delete().eq("id", project_id)
    if enterprise_id:
        q = q.eq("enterprise_id", enterprise_id)
    q.execute()

    left = sb.table("projects").select("id").eq("id", project_id).limit(1).execute()
    if left.data:
        raise HTTPException(500, "failed to delete project")
    return {"ok": True, "id": project_id}

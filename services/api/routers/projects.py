"""
QCSpec · 项目路由
services/api/routers/projects.py
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from supabase import create_client, Client
import os, re
import csv
from io import StringIO

router = APIRouter()

def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    return create_client(url, key)

def slugify(name: str) -> str:
    """项目名 → v:// slug"""
    return re.sub(r'[（）()\s【】《》""\'\'·，。！？、；：]', '', name)[:20] or 'project'

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
        summary = row.get("summary") or f"{obj or 'object'} {action or 'update'}"
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
    # 生成 v:// URI
    slug = slugify(body.name)
    v_uri = f"v://cn.企业/{body.type}/{slug}/"

    # 检查重复
    exist = sb.table("projects").select("id")\
               .eq("v_uri", v_uri).execute()
    if exist.data:
        raise HTTPException(409, f"节点已存在：{v_uri}")

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
        raise HTTPException(500, "创建失败")

    proj = res.data[0]
    return {
        "id":    proj["id"],
        "v_uri": proj["v_uri"],
        "name":  proj["name"],
    }

@router.get("/{project_id}")
async def get_project(
    project_id: str,
    sb: Client  = Depends(get_supabase),
):
    res = sb.table("projects").select("*")\
            .eq("id", project_id).single().execute()
    if not res.data:
        raise HTTPException(404, "项目不存在")
    return res.data

@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    updates: dict,
    sb: Client = Depends(get_supabase),
):
    res = sb.table("projects").update(updates)\
            .eq("id", project_id).execute()
    return res.data[0] if res.data else {}


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    enterprise_id: Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    q = sb.table("projects").delete().eq("id", project_id)
    if enterprise_id:
        q = q.eq("enterprise_id", enterprise_id)
    res = q.execute()
    if not res.data:
        raise HTTPException(404, "椤圭洰涓嶅瓨鍦ㄦ垨鏃犳潈鍒犻櫎")
    return {"ok": True, "id": project_id}

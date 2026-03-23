"""
QCSpec · 质检记录路由
services/api/routers/inspections.py
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from supabase import create_client, Client
import os, hashlib, json

router = APIRouter()

def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise HTTPException(500, "Supabase 未配置")
    return create_client(url, key)

# ── 请求模型 ──
class InspectionCreate(BaseModel):
    project_id:    str
    location:      str
    type:          str
    type_name:     str
    value:         float
    standard:      Optional[float] = None
    unit:          str = ""
    result:        str   # pass / warn / fail
    person:        Optional[str] = None
    remark:        Optional[str] = None
    inspected_at:  Optional[str] = None
    photo_ids:     Optional[List[str]] = []

class InspectionFilter(BaseModel):
    result:    Optional[str] = None
    type:      Optional[str] = None
    location:  Optional[str] = None
    date_from: Optional[str] = None
    date_to:   Optional[str] = None

# ── 生成 Proof ──
def _gen_proof(v_uri: str, data: dict) -> str:
    payload = json.dumps({
        "uri": v_uri,
        "data": data,
        "ts": datetime.utcnow().isoformat(),
    }, ensure_ascii=False, sort_keys=True)
    h = hashlib.sha256(payload.encode()).hexdigest()[:16].upper()
    return f"GP-PROOF-{h}"

# ── 路由 ──

@router.get("/")
async def list_inspections(
    project_id: str,
    result:     Optional[str] = None,
    type:       Optional[str] = None,
    limit:      int = Query(50, le=200),
    offset:     int = 0,
    sb: Client  = Depends(get_supabase),
):
    """查询质检记录列表"""
    q = sb.table("inspections")\
          .select("*")\
          .eq("project_id", project_id)\
          .order("inspected_at", desc=True)\
          .range(offset, offset + limit - 1)

    if result: q = q.eq("result", result)
    if type:   q = q.eq("type", type)

    res = q.execute()
    return {"data": res.data, "count": len(res.data)}


@router.post("/", status_code=201)
async def create_inspection(
    body: InspectionCreate,
    sb:   Client = Depends(get_supabase),
):
    """
    提交质检记录
    自动生成 v:// URI + Proof Hash
    """
    # 获取项目 v:// URI
    proj = sb.table("projects").select("v_uri, enterprise_id")\
             .eq("id", body.project_id).single().execute()
    if not proj.data:
        raise HTTPException(404, "项目不存在")

    proj_uri = proj.data["v_uri"]
    ent_id   = proj.data["enterprise_id"]
    now      = body.inspected_at or datetime.utcnow().isoformat()

    # 插入记录（v_uri 由触发器自动生成）
    rec = {
        "project_id":    body.project_id,
        "enterprise_id": ent_id,
        "location":      body.location,
        "type":          body.type,
        "type_name":     body.type_name,
        "value":         body.value,
        "standard":      body.standard,
        "unit":          body.unit,
        "result":        body.result,
        "person":        body.person,
        "remark":        body.remark,
        "inspected_at":  now,
    }
    ins = sb.table("inspections").insert(rec).execute()
    if not ins.data:
        raise HTTPException(500, "写入失败")

    insp = ins.data[0]
    v_uri = insp.get("v_uri") or f"{proj_uri}inspection/{insp['id']}/"

    # 生成 Proof
    proof_id = _gen_proof(v_uri, {
        "value": body.value, "result": body.result, "location": body.location
    })

    # 回写 Proof
    sb.table("inspections").update({
        "proof_id": proof_id, "proof_status": "confirmed"
    }).eq("id", insp["id"]).execute()

    # 写入 Proof 链
    sb.table("proof_chain").insert({
        "proof_id":    proof_id,
        "proof_hash":  proof_id.replace("GP-PROOF-", "").lower(),
        "enterprise_id": ent_id,
        "project_id":  body.project_id,
        "v_uri":       v_uri,
        "object_type": "inspection",
        "object_id":   insp["id"],
        "action":      "create",
        "summary":     f"质检录入·{body.type_name}·{body.location}·{body.result}",
        "status":      "confirmed",
    }).execute()

    return {
        "inspection_id": insp["id"],
        "v_uri":         v_uri,
        "proof_id":      proof_id,
        "result":        body.result,
    }


@router.get("/stats/{project_id}")
async def project_stats(
    project_id: str,
    sb: Client  = Depends(get_supabase),
):
    """项目质检统计"""
    res = sb.table("inspections")\
            .select("result")\
            .eq("project_id", project_id)\
            .execute()
    rows = res.data or []
    total  = len(rows)
    passed = sum(1 for r in rows if r["result"] == "pass")
    warned = sum(1 for r in rows if r["result"] == "warn")
    failed = sum(1 for r in rows if r["result"] == "fail")
    return {
        "total":     total,
        "pass":      passed,
        "warn":      warned,
        "fail":      failed,
        "pass_rate": round(passed / total * 100, 1) if total else 0,
    }


@router.delete("/{inspection_id}")
async def delete_inspection(
    inspection_id: str,
    sb: Client = Depends(get_supabase),
):
    """删除质检记录"""
    sb.table("inspections").delete().eq("id", inspection_id).execute()
    return {"ok": True}

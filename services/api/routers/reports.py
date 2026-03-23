"""
QCSpec · 报告路由
services/api/routers/reports.py
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from supabase import create_client, Client
from datetime import datetime
import os, sys, hashlib, json

router = APIRouter()

def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    return create_client(url, key)

class ReportRequest(BaseModel):
    project_id:    str
    enterprise_id: str
    location:      Optional[str] = None
    date_from:     Optional[str] = None
    date_to:       Optional[str] = None

def _gen_proof(v_uri: str, data: dict) -> str:
    payload = json.dumps({"uri": v_uri, "data": data, "ts": datetime.utcnow().isoformat()}, sort_keys=True)
    h = hashlib.sha256(payload.encode()).hexdigest()[:16].upper()
    return f"GP-PROOF-{h}"

def _generate_report_task(project_id: str, ent_id: str, location: Optional[str], supabase_url: str, supabase_key: str):
    """后台任务：调用 Python 报告引擎生成 Word 文件"""
    from supabase import create_client
    sb = create_client(supabase_url, supabase_key)

    # 拉取质检数据
    q = sb.table("inspections").select("*").eq("project_id", project_id)
    if location:
        q = q.eq("location", location)
    records = q.execute().data or []

    # 拉取照片
    photos = sb.table("photos").select("*")\
               .eq("project_id", project_id).execute().data or []

    # 拉取项目配置
    proj = sb.table("projects").select("v_uri, name, contract_no, supervisor")\
             .eq("id", project_id).single().execute().data

    if not proj:
        return

    # 统计
    total  = len(records)
    passed = sum(1 for r in records if r["result"] == "pass")
    warned = sum(1 for r in records if r["result"] == "warn")
    failed = sum(1 for r in records if r["result"] == "fail")
    rate   = round(passed / total * 100, 1) if total else 0

    # 生成报告编号
    now = datetime.utcnow()
    report_no = f"QC-{now.strftime('%Y%m%d%H%M%S')}"

    # v:// URI
    report_uri = f"{proj['v_uri']}reports/{report_no}/"
    proof_id   = _gen_proof(report_uri, {"total": total, "pass_rate": rate})

    # 结论
    if failed == 0 and warned == 0:
        conclusion = "✓ 全部合格 — 本次检测所有项目均符合规范要求"
    elif failed == 0:
        conclusion = f"⚠ 基本合格 — {warned}项需持续观察"
    else:
        conclusion = f"✗ 存在不合格项 — {failed}项不合格，必须整改后复测"

    fail_items = "；".join(
        f"{r.get('type_name', r['type'])}（{r['location']}）"
        for r in records if r["result"] == "fail"
    ) or "无"

    # 写入报告表
    sb.table("reports").insert({
        "project_id":    project_id,
        "enterprise_id": ent_id,
        "v_uri":         report_uri,
        "report_no":     report_no,
        "location":      location,
        "total_count":   total,
        "pass_count":    passed,
        "warn_count":    warned,
        "fail_count":    failed,
        "pass_rate":     rate,
        "conclusion":    conclusion,
        "fail_items":    fail_items,
        "proof_id":      proof_id,
        "proof_status":  "confirmed",
        "inspection_ids": [r["id"] for r in records],
        "photo_ids":     [p["id"] for p in photos],
    }).execute()

    # 写入 Proof 链
    sb.table("proof_chain").insert({
        "proof_id":      proof_id,
        "proof_hash":    proof_id.replace("GP-PROOF-", "").lower(),
        "enterprise_id": ent_id,
        "project_id":    project_id,
        "v_uri":         report_uri,
        "object_type":   "report",
        "action":        "generate",
        "summary":       f"报告生成·{report_no}·合格率{rate}%",
        "status":        "confirmed",
    }).execute()

    print(f"✅ 报告生成完成：{report_no} · {report_uri}")


@router.post("/generate", status_code=202)
async def generate_report(
    body: ReportRequest,
    background_tasks: BackgroundTasks,
    sb: Client = Depends(get_supabase),
):
    """触发报告生成（异步后台任务）"""
    background_tasks.add_task(
        _generate_report_task,
        body.project_id,
        body.enterprise_id,
        body.location,
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY"),
    )
    return {"accepted": True, "message": "报告生成中，请稍后查询"}


@router.get("/")
async def list_reports(
    project_id: str,
    sb: Client  = Depends(get_supabase),
):
    res = sb.table("reports").select("*")\
            .eq("project_id", project_id)\
            .order("generated_at", desc=True).execute()
    return {"data": res.data}


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    sb: Client = Depends(get_supabase),
):
    res = sb.table("reports").select("*")\
            .eq("id", report_id).single().execute()
    if not res.data:
        raise HTTPException(404, "报告不存在")
    return res.data

"""
Enterprise settings routes for QCSpec.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from supabase import Client, create_client

router = APIRouter()

DEFAULT_PERMISSION_MATRIX = [
    {"role": "OWNER", "view": True, "input": True, "approve": True, "manage": True, "settle": True, "regulator": True},
    {"role": "SUPERVISOR", "view": True, "input": True, "approve": True, "manage": False, "settle": False, "regulator": False},
    {"role": "AI", "view": True, "input": True, "approve": False, "manage": False, "settle": False, "regulator": False},
    {"role": "PUBLIC", "view": True, "input": False, "approve": False, "manage": False, "settle": False, "regulator": False},
    {"role": "REGULATOR", "view": True, "input": False, "approve": False, "manage": False, "settle": False, "regulator": True},
]


def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    return create_client(url, key)


class SettingsUpdate(BaseModel):
    enterpriseName: Optional[str] = None
    enterpriseVUri: Optional[str] = None
    enterpriseCreditCode: Optional[str] = None
    emailNotify: Optional[bool] = None
    wechatNotify: Optional[bool] = None
    autoGenerateReport: Optional[bool] = None
    strictProof: Optional[bool] = None
    reportTemplate: Optional[str] = None
    reportHeader: Optional[str] = None
    webhookUrl: Optional[str] = None
    gitpegToken: Optional[str] = None
    gitpegEnabled: Optional[bool] = None
    erpnextSync: Optional[bool] = None
    wechatMiniapp: Optional[bool] = None
    droneImport: Optional[bool] = None
    permissionMatrix: Optional[list[dict]] = None


def _normalize_permission_matrix(rows: Optional[list[dict]]) -> list[dict]:
    if not rows:
        return list(DEFAULT_PERMISSION_MATRIX)

    normalized_by_role: dict[str, dict] = {}
    for row in rows:
        role = str(row.get("role") or "").upper()
        if role not in {"OWNER", "SUPERVISOR", "AI", "PUBLIC", "REGULATOR", "MARKET"}:
            continue
        normalized_by_role[role] = {
            "role": role,
            "view": bool(row.get("view", False)),
            "input": bool(row.get("input", False)),
            "approve": bool(row.get("approve", False)),
            "manage": bool(row.get("manage", False)),
            "settle": bool(row.get("settle", False)),
            "regulator": bool(row.get("regulator", False)),
        }

    if not normalized_by_role:
        return list(DEFAULT_PERMISSION_MATRIX)

    merged: list[dict] = []
    for default_row in DEFAULT_PERMISSION_MATRIX:
        role = default_row["role"]
        override = normalized_by_role.get(role)
        merged.append({**default_row, **(override or {}), "role": role})

    market = normalized_by_role.get("MARKET")
    if market:
        merged.append(market)

    return merged


def _ensure_config(sb: Client, enterprise_id: str) -> dict:
    row = sb.table("enterprise_configs").select("*").eq("enterprise_id", enterprise_id).limit(1).execute()
    if row.data:
        return row.data[0]
    created = sb.table("enterprise_configs").insert({"enterprise_id": enterprise_id}).execute()
    if not created.data:
        raise HTTPException(500, "failed to create enterprise config")
    return created.data[0]


def _to_payload(cfg: dict, ent: dict) -> dict:
    custom = cfg.get("custom_fields") or {}
    matrix = _normalize_permission_matrix(custom.get("permission_matrix"))
    return {
        "enterprise": {
            "id": ent.get("id"),
            "name": ent.get("name"),
            "v_uri": ent.get("v_uri"),
            "credit_code": ent.get("credit_code"),
        },
        "settings": {
            "emailNotify": bool(cfg.get("notify_daily", True)),
            "wechatNotify": bool(cfg.get("wechat_enabled", True)),
            "autoGenerateReport": bool(custom.get("auto_generate_report", False)),
            "strictProof": bool(custom.get("strict_proof", True)),
            "reportTemplate": cfg.get("report_template") or "default.docx",
            "reportTemplateUrl": custom.get("report_template_url") or "",
            "reportHeader": custom.get("report_header") or ent.get("name") or "",
            "webhookUrl": custom.get("webhook_url") or "",
            "gitpegToken": custom.get("gitpeg_token") or "",
            "gitpegEnabled": bool(custom.get("gitpeg_enabled", False)),
            "erpnextSync": bool(custom.get("erpnext_sync", False)),
            "wechatMiniapp": bool(custom.get("wechat_miniapp", True)),
            "droneImport": bool(custom.get("drone_import", False)),
            "permissionMatrix": matrix,
        },
    }


@router.get("/")
async def get_settings(enterprise_id: str, sb: Client = Depends(get_supabase)):
    ent = sb.table("enterprises").select("id,name,v_uri,credit_code").eq("id", enterprise_id).single().execute()
    if not ent.data:
        raise HTTPException(404, "enterprise not found")
    cfg = _ensure_config(sb, enterprise_id)
    return _to_payload(cfg, ent.data)


@router.post("/template/upload")
async def upload_template(
    enterprise_id: str = Form(...),
    file: UploadFile = File(...),
    sb: Client = Depends(get_supabase),
):
    if not file.filename:
        raise HTTPException(400, "template file is required")
    if not file.content_type or not (
        file.content_type == "application/msword"
        or file.content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or file.filename.lower().endswith((".doc", ".docx"))
    ):
        raise HTTPException(400, "only .doc/.docx template is supported")

    ent = sb.table("enterprises").select("id,name,v_uri,credit_code").eq("id", enterprise_id).single().execute()
    if not ent.data:
        raise HTTPException(404, "enterprise not found")

    cfg = _ensure_config(sb, enterprise_id)
    custom = dict(cfg.get("custom_fields") or {})

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, "template exceeds 20MB")

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = file.filename.replace(" ", "_")
    storage_path = f"{enterprise_id}/{ts}_{safe_name}"

    try:
        sb.storage.from_("qcspec-templates").upload(
            storage_path,
            content,
            file_options={"content-type": file.content_type or "application/octet-stream"},
        )
        public_url = sb.storage.from_("qcspec-templates").get_public_url(storage_path)
    except Exception as exc:
        raise HTTPException(500, f"failed to upload template: {exc}") from exc

    template_url = public_url if isinstance(public_url, str) else ""
    updates = {
        "report_template": file.filename,
        "custom_fields": {
            **custom,
            "report_template_path": storage_path,
            "report_template_url": template_url,
        },
    }

    res = sb.table("enterprise_configs").update(updates).eq("enterprise_id", enterprise_id).execute()
    if not res.data:
        raise HTTPException(500, "failed to update template settings")

    return _to_payload(res.data[0], ent.data)


@router.patch("/")
async def update_settings(
    enterprise_id: str,
    body: SettingsUpdate,
    sb: Client = Depends(get_supabase),
):
    ent = sb.table("enterprises").select("id,name,v_uri,credit_code").eq("id", enterprise_id).single().execute()
    if not ent.data:
        raise HTTPException(404, "enterprise not found")
    ent_data = ent.data

    cfg = _ensure_config(sb, enterprise_id)
    custom = dict(cfg.get("custom_fields") or {})
    updates: dict = {}
    enterprise_updates: dict = {}

    if body.enterpriseName is not None:
        enterprise_updates["name"] = body.enterpriseName
    if body.enterpriseVUri is not None:
        enterprise_updates["v_uri"] = body.enterpriseVUri
    if body.enterpriseCreditCode is not None:
        enterprise_updates["credit_code"] = body.enterpriseCreditCode
    if enterprise_updates:
        ent_upd = sb.table("enterprises").update(enterprise_updates).eq("id", enterprise_id).execute()
        if not ent_upd.data:
            raise HTTPException(500, "failed to update enterprise")
        ent_data = ent_upd.data[0]

    if body.emailNotify is not None:
        updates["notify_daily"] = body.emailNotify
    if body.wechatNotify is not None:
        updates["wechat_enabled"] = body.wechatNotify
    if body.reportTemplate is not None:
        updates["report_template"] = body.reportTemplate

    if body.autoGenerateReport is not None:
        custom["auto_generate_report"] = body.autoGenerateReport
    if body.strictProof is not None:
        custom["strict_proof"] = body.strictProof
    if body.reportHeader is not None:
        custom["report_header"] = body.reportHeader
    if body.webhookUrl is not None:
        custom["webhook_url"] = body.webhookUrl
    if body.gitpegToken is not None:
        custom["gitpeg_token"] = body.gitpegToken
    if body.gitpegEnabled is not None:
        custom["gitpeg_enabled"] = body.gitpegEnabled
    if body.erpnextSync is not None:
        custom["erpnext_sync"] = body.erpnextSync
    if body.wechatMiniapp is not None:
        custom["wechat_miniapp"] = body.wechatMiniapp
    if body.droneImport is not None:
        custom["drone_import"] = body.droneImport
    if body.permissionMatrix is not None:
        custom["permission_matrix"] = _normalize_permission_matrix(body.permissionMatrix)

    updates["custom_fields"] = custom

    res = sb.table("enterprise_configs").update(updates).eq("enterprise_id", enterprise_id).execute()
    if not res.data:
        raise HTTPException(500, "failed to update settings")

    latest = res.data[0]
    return _to_payload(latest, ent_data)

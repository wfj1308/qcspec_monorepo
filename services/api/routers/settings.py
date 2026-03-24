"""
Enterprise settings routes for QCSpec.
"""

from __future__ import annotations

import os
import time
from functools import lru_cache
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
import httpx
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


@lru_cache(maxsize=1)
def _supabase_client_cached(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase() -> Client:
    url = str(os.getenv("SUPABASE_URL") or "").strip()
    key = str(os.getenv("SUPABASE_SERVICE_KEY") or "").strip()
    if not url or not key:
        raise HTTPException(500, "Supabase not configured")
    return _supabase_client_cached(url, key)


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
    erpnextUrl: Optional[str] = None
    erpnextSiteName: Optional[str] = None
    erpnextApiKey: Optional[str] = None
    erpnextApiSecret: Optional[str] = None
    erpnextProjectDoctype: Optional[str] = None
    erpnextProjectLookupField: Optional[str] = None
    erpnextProjectLookupValue: Optional[str] = None
    erpnextGitpegProjectUriField: Optional[str] = None
    erpnextGitpegSiteUriField: Optional[str] = None
    erpnextGitpegStatusField: Optional[str] = None
    erpnextGitpegResultJsonField: Optional[str] = None
    wechatMiniapp: Optional[bool] = None
    droneImport: Optional[bool] = None
    permissionMatrix: Optional[list[dict]] = None


class ErpNextTestRequest(BaseModel):
    url: str
    siteName: Optional[str] = None
    apiKey: Optional[str] = None
    apiSecret: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    timeoutMs: Optional[int] = 8000


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


def _normalize_erp_url(raw: Optional[str]) -> str:
    value = str(raw or "").strip().rstrip("/")
    if not value:
        raise HTTPException(400, "ERPNext URL is required")
    if not value.startswith("http://") and not value.startswith("https://"):
        value = f"http://{value}"
    return value


def _erp_headers(site_name: Optional[str]) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "QCSpec-ERPNext-Test/1.0",
    }
    site = str(site_name or "").strip()
    if site:
        headers["Host"] = site
        headers["X-Forwarded-Host"] = site
        headers["X-Frappe-Site-Name"] = site
    return headers


def _auth_candidates(api_key: Optional[str], api_secret: Optional[str]) -> list[tuple[str, str]]:
    key = str(api_key or "").strip()
    secret = str(api_secret or "").strip()
    candidates: list[tuple[str, str]] = []
    if key and secret:
        candidates.append(("token", f"token {key}:{secret}"))
    elif key:
        lower = key.lower()
        if lower.startswith("token "):
            candidates.append(("token", key))
        elif lower.startswith("bearer "):
            candidates.append(("bearer", key))
        elif ":" in key:
            candidates.append(("token", f"token {key}"))
        else:
            # Some self-hosted gateways only accept Bearer.
            candidates.append(("bearer", f"Bearer {key}"))
    return candidates


def _extract_logged_user(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    message = payload.get("message")
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        user = message.get("user") or message.get("email") or message.get("name")
        return str(user or "")
    user = payload.get("user")
    return str(user or "")


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
            "erpnextUrl": custom.get("erpnext_url") or "",
            "erpnextSiteName": custom.get("erpnext_site_name") or "",
            "erpnextApiKey": custom.get("erpnext_api_key") or "",
            "erpnextApiSecret": custom.get("erpnext_api_secret") or "",
            "erpnextProjectDoctype": custom.get("erpnext_project_doctype") or "Project",
            "erpnextProjectLookupField": custom.get("erpnext_project_lookup_field") or "name",
            "erpnextProjectLookupValue": custom.get("erpnext_project_lookup_value") or "",
            "erpnextGitpegProjectUriField": custom.get("erpnext_gitpeg_project_uri_field") or "gitpeg_project_uri",
            "erpnextGitpegSiteUriField": custom.get("erpnext_gitpeg_site_uri_field") or "gitpeg_site_uri",
            "erpnextGitpegStatusField": custom.get("erpnext_gitpeg_status_field") or "gitpeg_status",
            "erpnextGitpegResultJsonField": custom.get("erpnext_gitpeg_result_json_field")
            or "gitpeg_register_result_json",
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


@router.post("/erpnext/test")
async def test_erpnext_connection(body: ErpNextTestRequest):
    url = _normalize_erp_url(body.url)
    site_name = str(body.siteName or "").strip() or None
    username = str(body.username or "").strip()
    password = str(body.password or "").strip()
    timeout_ms = int(body.timeoutMs or 8000)
    timeout_s = min(max(timeout_ms / 1000, 2.0), 30.0)

    headers = _erp_headers(site_name)
    health_url = f"{url}/api/method/frappe.auth.get_logged_user"
    errors: list[str] = []
    started_at = time.perf_counter()

    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
        for mode, auth_header in _auth_candidates(body.apiKey, body.apiSecret):
            req_headers = {**headers, "Authorization": auth_header}
            try:
                res = await client.get(health_url, headers=req_headers)
                if res.status_code >= 400:
                    errors.append(f"{mode}:{res.status_code}")
                    continue
                payload = res.json()
                user = _extract_logged_user(payload)
                latency_ms = int((time.perf_counter() - started_at) * 1000)
                return {
                    "ok": True,
                    "authMode": mode,
                    "message": "ERPNext connection successful",
                    "erpUrl": url,
                    "siteName": site_name or "",
                    "user": user,
                    "latencyMs": latency_ms,
                }
            except httpx.TimeoutException:
                errors.append(f"{mode}:timeout")
            except Exception as exc:
                errors.append(f"{mode}:{str(exc)}")

        if username and password:
            try:
                login_res = await client.post(
                    f"{url}/api/method/login",
                    headers=headers,
                    data={"usr": username, "pwd": password},
                )
                if login_res.status_code >= 400:
                    errors.append(f"session_login:{login_res.status_code}")
                else:
                    check_res = await client.get(health_url, headers=headers)
                    if check_res.status_code >= 400:
                        errors.append(f"session_check:{check_res.status_code}")
                    else:
                        payload = check_res.json()
                        user = _extract_logged_user(payload) or username
                        latency_ms = int((time.perf_counter() - started_at) * 1000)
                        return {
                            "ok": True,
                            "authMode": "session",
                            "message": "ERPNext connection successful",
                            "erpUrl": url,
                            "siteName": site_name or "",
                            "user": user,
                            "latencyMs": latency_ms,
                        }
            except httpx.TimeoutException:
                errors.append("session:timeout")
            except Exception as exc:
                errors.append(f"session:{str(exc)}")

    detail = "; ".join(errors) if errors else "no valid auth info provided"
    raise HTTPException(502, f"failed to connect ERPNext ({detail})")


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
    if body.erpnextUrl is not None:
        custom["erpnext_url"] = body.erpnextUrl.strip()
    if body.erpnextSiteName is not None:
        custom["erpnext_site_name"] = body.erpnextSiteName.strip()
    if body.erpnextApiKey is not None:
        custom["erpnext_api_key"] = body.erpnextApiKey.strip()
    if body.erpnextApiSecret is not None:
        custom["erpnext_api_secret"] = body.erpnextApiSecret.strip()
    if body.erpnextProjectDoctype is not None:
        custom["erpnext_project_doctype"] = body.erpnextProjectDoctype.strip()
    if body.erpnextProjectLookupField is not None:
        custom["erpnext_project_lookup_field"] = body.erpnextProjectLookupField.strip()
    if body.erpnextProjectLookupValue is not None:
        custom["erpnext_project_lookup_value"] = body.erpnextProjectLookupValue.strip()
    if body.erpnextGitpegProjectUriField is not None:
        custom["erpnext_gitpeg_project_uri_field"] = body.erpnextGitpegProjectUriField.strip()
    if body.erpnextGitpegSiteUriField is not None:
        custom["erpnext_gitpeg_site_uri_field"] = body.erpnextGitpegSiteUriField.strip()
    if body.erpnextGitpegStatusField is not None:
        custom["erpnext_gitpeg_status_field"] = body.erpnextGitpegStatusField.strip()
    if body.erpnextGitpegResultJsonField is not None:
        custom["erpnext_gitpeg_result_json_field"] = body.erpnextGitpegResultJsonField.strip()
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

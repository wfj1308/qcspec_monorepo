"""
Enterprise settings business service.
services/api/settings_service.py
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException
from supabase import Client

from services.api.settings_connection_service import (
    test_erpnext_connection_flow,
    test_gitpeg_registrar_connection_flow,
)

DEFAULT_PERMISSION_MATRIX = [
    {"role": "OWNER", "view": True, "input": True, "approve": True, "manage": True, "settle": True, "regulator": True},
    {"role": "SUPERVISOR", "view": True, "input": True, "approve": True, "manage": False, "settle": False, "regulator": False},
    {"role": "AI", "view": True, "input": True, "approve": False, "manage": False, "settle": False, "regulator": False},
    {"role": "PUBLIC", "view": True, "input": False, "approve": False, "manage": False, "settle": False, "regulator": False},
    {"role": "REGULATOR", "view": True, "input": False, "approve": False, "manage": False, "settle": False, "regulator": True},
]


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
            "gitpegRegistrarBaseUrl": custom.get("gitpeg_registrar_base_url")
            or os.getenv("GITPEG_REGISTRAR_BASE_URL")
            or "https://gitpeg.cn",
            "gitpegPartnerCode": custom.get("gitpeg_partner_code") or os.getenv("GITPEG_PARTNER_CODE") or "",
            "gitpegIndustryCode": custom.get("gitpeg_industry_code") or os.getenv("GITPEG_INDUSTRY_CODE") or "",
            "gitpegClientId": custom.get("gitpeg_client_id") or os.getenv("GITPEG_CLIENT_ID") or "",
            "gitpegClientSecret": custom.get("gitpeg_client_secret") or os.getenv("GITPEG_CLIENT_SECRET") or "",
            "gitpegRegistrationMode": custom.get("gitpeg_registration_mode")
            or os.getenv("GITPEG_REGISTRATION_MODE")
            or "DOMAIN",
            "gitpegReturnUrl": custom.get("gitpeg_return_url") or os.getenv("GITPEG_RETURN_URL") or "",
            "gitpegWebhookUrl": custom.get("gitpeg_webhook_url") or os.getenv("GITPEG_WEBHOOK_URL") or "",
            "gitpegWebhookSecret": custom.get("gitpeg_webhook_secret") or "",
            "gitpegModuleCandidates": custom.get("gitpeg_module_candidates")
            or [
                item.strip()
                for item in str(os.getenv("GITPEG_MODULE_CANDIDATES") or "proof,utrip,openapi").split(",")
                if item.strip()
            ],
            "erpnextSync": bool(custom.get("erpnext_sync", False)),
            "erpnextUrl": custom.get("erpnext_url") or "",
            "erpnextSiteName": custom.get("erpnext_site_name") or "",
            "erpnextApiKey": custom.get("erpnext_api_key") or "",
            "erpnextApiSecret": custom.get("erpnext_api_secret") or "",
            "erpnextUsername": custom.get("erpnext_username") or "",
            "erpnextPassword": custom.get("erpnext_password") or "",
            "erpnextProjectDoctype": custom.get("erpnext_project_doctype") or "Project",
            "erpnextProjectLookupField": custom.get("erpnext_project_lookup_field") or "name",
            "erpnextProjectLookupValue": custom.get("erpnext_project_lookup_value") or "",
            "erpnextGitpegProjectUriField": custom.get("erpnext_gitpeg_project_uri_field") or "gitpeg_project_uri",
            "erpnextGitpegSiteUriField": custom.get("erpnext_gitpeg_site_uri_field") or "gitpeg_site_uri",
            "erpnextGitpegStatusField": custom.get("erpnext_gitpeg_status_field") or "gitpeg_status",
            "erpnextGitpegResultJsonField": custom.get("erpnext_gitpeg_result_json_field")
            or "gitpeg_register_result_json",
            "erpnextGitpegRegistrationIdField": custom.get("erpnext_gitpeg_registration_id_field")
            or "gitpeg_registration_id",
            "erpnextGitpegNodeUriField": custom.get("erpnext_gitpeg_node_uri_field") or "gitpeg_node_uri",
            "erpnextGitpegShellUriField": custom.get("erpnext_gitpeg_shell_uri_field") or "gitpeg_shell_uri",
            "erpnextGitpegProofHashField": custom.get("erpnext_gitpeg_proof_hash_field") or "gitpeg_proof_hash",
            "erpnextGitpegIndustryProfileIdField": custom.get("erpnext_gitpeg_industry_profile_id_field")
            or "gitpeg_industry_profile_id",
            "wechatMiniapp": bool(custom.get("wechat_miniapp", True)),
            "droneImport": bool(custom.get("drone_import", False)),
            "permissionMatrix": matrix,
        },
    }


async def get_settings_flow(*, enterprise_id: str, sb: Client) -> dict[str, Any]:
    ent = sb.table("enterprises").select("id,name,v_uri,credit_code").eq("id", enterprise_id).single().execute()
    if not ent.data:
        raise HTTPException(404, "enterprise not found")
    cfg = _ensure_config(sb, enterprise_id)
    return _to_payload(cfg, ent.data)


async def upload_template_flow(*, enterprise_id: str, file: Any, sb: Client) -> dict[str, Any]:
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


async def update_settings_flow(
    *,
    enterprise_id: str,
    body: Any,
    sb: Client,
) -> dict[str, Any]:
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
    if body.gitpegRegistrarBaseUrl is not None:
        custom["gitpeg_registrar_base_url"] = body.gitpegRegistrarBaseUrl.strip()
    if body.gitpegPartnerCode is not None:
        custom["gitpeg_partner_code"] = body.gitpegPartnerCode.strip()
    if body.gitpegIndustryCode is not None:
        custom["gitpeg_industry_code"] = body.gitpegIndustryCode.strip()
    if body.gitpegClientId is not None:
        custom["gitpeg_client_id"] = body.gitpegClientId.strip()
    if body.gitpegClientSecret is not None:
        custom["gitpeg_client_secret"] = body.gitpegClientSecret.strip()
    if body.gitpegRegistrationMode is not None:
        custom["gitpeg_registration_mode"] = body.gitpegRegistrationMode.strip().upper()
    if body.gitpegReturnUrl is not None:
        custom["gitpeg_return_url"] = body.gitpegReturnUrl.strip()
    if body.gitpegWebhookUrl is not None:
        custom["gitpeg_webhook_url"] = body.gitpegWebhookUrl.strip()
    if body.gitpegWebhookSecret is not None:
        custom["gitpeg_webhook_secret"] = body.gitpegWebhookSecret.strip()
    if body.gitpegModuleCandidates is not None:
        custom["gitpeg_module_candidates"] = [
            str(item).strip()
            for item in body.gitpegModuleCandidates
            if str(item).strip()
        ]
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
    if body.erpnextUsername is not None:
        custom["erpnext_username"] = body.erpnextUsername.strip()
    if body.erpnextPassword is not None:
        custom["erpnext_password"] = body.erpnextPassword.strip()
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
    if body.erpnextGitpegRegistrationIdField is not None:
        custom["erpnext_gitpeg_registration_id_field"] = body.erpnextGitpegRegistrationIdField.strip()
    if body.erpnextGitpegNodeUriField is not None:
        custom["erpnext_gitpeg_node_uri_field"] = body.erpnextGitpegNodeUriField.strip()
    if body.erpnextGitpegShellUriField is not None:
        custom["erpnext_gitpeg_shell_uri_field"] = body.erpnextGitpegShellUriField.strip()
    if body.erpnextGitpegProofHashField is not None:
        custom["erpnext_gitpeg_proof_hash_field"] = body.erpnextGitpegProofHashField.strip()
    if body.erpnextGitpegIndustryProfileIdField is not None:
        custom["erpnext_gitpeg_industry_profile_id_field"] = body.erpnextGitpegIndustryProfileIdField.strip()
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

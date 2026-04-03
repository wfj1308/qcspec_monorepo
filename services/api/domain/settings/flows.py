"""Canonical settings-domain flow entry points."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable, Optional

from fastapi import HTTPException, UploadFile
from supabase import Client

from services.api.core.http import read_upload_content_async

ENTERPRISE_SELECT_FIELDS = "id,name,v_uri,credit_code"
TEMPLATE_MAX_BYTES = 20 * 1024 * 1024
TEMPLATE_CONTENT_TYPES = {
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

DEFAULT_PERMISSION_MATRIX = [
    {"role": "OWNER", "view": True, "input": True, "approve": True, "manage": True, "settle": True, "regulator": True},
    {"role": "SUPERVISOR", "view": True, "input": True, "approve": True, "manage": False, "settle": False, "regulator": False},
    {"role": "AI", "view": True, "input": True, "approve": False, "manage": False, "settle": False, "regulator": False},
    {"role": "PUBLIC", "view": True, "input": False, "approve": False, "manage": False, "settle": False, "regulator": False},
    {"role": "REGULATOR", "view": True, "input": False, "approve": False, "manage": False, "settle": False, "regulator": True},
]

ENTERPRISE_UPDATE_FIELD_MAP = {
    "enterpriseName": "name",
    "enterpriseVUri": "v_uri",
    "enterpriseCreditCode": "credit_code",
}

SETTINGS_UPDATE_FIELD_MAP = {
    "emailNotify": "notify_daily",
    "reportTemplate": "report_template",
}

CUSTOM_PASSTHROUGH_FIELD_MAP = {
    "autoGenerateReport": "auto_generate_report",
    "strictProof": "strict_proof",
    "reportHeader": "report_header",
    "webhookUrl": "webhook_url",
    "gitpegToken": "gitpeg_token",
    "gitpegEnabled": "gitpeg_enabled",
    "erpnextSync": "erpnext_sync",
    "droneImport": "drone_import",
}

CUSTOM_STRIP_FIELD_MAP = {
    "gitpegRegistrarBaseUrl": "gitpeg_registrar_base_url",
    "gitpegPartnerCode": "gitpeg_partner_code",
    "gitpegIndustryCode": "gitpeg_industry_code",
    "gitpegClientId": "gitpeg_client_id",
    "gitpegClientSecret": "gitpeg_client_secret",
    "gitpegReturnUrl": "gitpeg_return_url",
    "gitpegWebhookUrl": "gitpeg_webhook_url",
    "gitpegWebhookSecret": "gitpeg_webhook_secret",
    "erpnextUrl": "erpnext_url",
    "erpnextSiteName": "erpnext_site_name",
    "erpnextApiKey": "erpnext_api_key",
    "erpnextApiSecret": "erpnext_api_secret",
    "erpnextUsername": "erpnext_username",
    "erpnextPassword": "erpnext_password",
    "erpnextProjectDoctype": "erpnext_project_doctype",
    "erpnextProjectLookupField": "erpnext_project_lookup_field",
    "erpnextProjectLookupValue": "erpnext_project_lookup_value",
    "erpnextGitpegProjectUriField": "erpnext_gitpeg_project_uri_field",
    "erpnextGitpegSiteUriField": "erpnext_gitpeg_site_uri_field",
    "erpnextGitpegStatusField": "erpnext_gitpeg_status_field",
    "erpnextGitpegResultJsonField": "erpnext_gitpeg_result_json_field",
    "erpnextGitpegRegistrationIdField": "erpnext_gitpeg_registration_id_field",
    "erpnextGitpegNodeUriField": "erpnext_gitpeg_node_uri_field",
    "erpnextGitpegShellUriField": "erpnext_gitpeg_shell_uri_field",
    "erpnextGitpegProofHashField": "erpnext_gitpeg_proof_hash_field",
    "erpnextGitpegIndustryProfileIdField": "erpnext_gitpeg_industry_profile_id_field",
}

CUSTOM_UPPER_STRIP_FIELD_MAP = {
    "gitpegRegistrationMode": "gitpeg_registration_mode",
}


def _copy_present_fields(
    *,
    source: Any,
    target: dict[str, Any],
    field_map: dict[str, str],
    transform: Callable[[Any], Any] | None = None,
) -> None:
    for source_name, target_name in field_map.items():
        value = getattr(source, source_name, None)
        if value is None:
            continue
        target[target_name] = transform(value) if transform else value


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


def _get_enterprise_or_404(*, sb: Client, enterprise_id: str) -> dict[str, Any]:
    ent = sb.table("enterprises").select(ENTERPRISE_SELECT_FIELDS).eq("id", enterprise_id).single().execute()
    if not ent.data:
        raise HTTPException(404, "enterprise not found")
    return ent.data


def _is_supported_template(*, file: UploadFile) -> bool:
    content_type = str(file.content_type or "")
    return content_type in TEMPLATE_CONTENT_TYPES or str(file.filename or "").lower().endswith((".doc", ".docx"))


def _safe_template_filename(filename: str) -> str:
    # Keep storage path stable and avoid directory separators from client-provided names.
    sanitized = os.path.basename(filename).replace(" ", "_").strip()
    return sanitized or "template.docx"


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
            "droneImport": bool(custom.get("drone_import", False)),
            "permissionMatrix": matrix,
        },
    }


async def get_settings_flow(*, enterprise_id: str, sb: Client) -> dict[str, Any]:
    ent = _get_enterprise_or_404(sb=sb, enterprise_id=enterprise_id)
    cfg = _ensure_config(sb, enterprise_id)
    return _to_payload(cfg, ent)


async def upload_template_flow(*, enterprise_id: str, file: UploadFile, sb: Client) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(400, "template file is required")
    if not _is_supported_template(file=file):
        raise HTTPException(400, "only .doc/.docx template is supported")

    ent = _get_enterprise_or_404(sb=sb, enterprise_id=enterprise_id)

    cfg = _ensure_config(sb, enterprise_id)
    custom = dict(cfg.get("custom_fields") or {})

    content = await read_upload_content_async(
        file=file,
        max_bytes=TEMPLATE_MAX_BYTES,
        empty_error="template file is required",
        too_large_error="template exceeds 20MB",
    )

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = _safe_template_filename(file.filename)
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

    return _to_payload(res.data[0], ent)


async def update_settings_flow(
    *,
    enterprise_id: str,
    body: Any,
    sb: Client,
) -> dict[str, Any]:
    ent_data = _get_enterprise_or_404(sb=sb, enterprise_id=enterprise_id)

    cfg = _ensure_config(sb, enterprise_id)
    custom = dict(cfg.get("custom_fields") or {})
    updates: dict = {}
    enterprise_updates: dict = {}

    _copy_present_fields(
        source=body,
        target=enterprise_updates,
        field_map=ENTERPRISE_UPDATE_FIELD_MAP,
    )
    if enterprise_updates:
        ent_upd = sb.table("enterprises").update(enterprise_updates).eq("id", enterprise_id).execute()
        if not ent_upd.data:
            raise HTTPException(500, "failed to update enterprise")
        ent_data = ent_upd.data[0]

    _copy_present_fields(
        source=body,
        target=updates,
        field_map=SETTINGS_UPDATE_FIELD_MAP,
    )
    _copy_present_fields(
        source=body,
        target=custom,
        field_map=CUSTOM_PASSTHROUGH_FIELD_MAP,
    )
    _copy_present_fields(
        source=body,
        target=custom,
        field_map=CUSTOM_STRIP_FIELD_MAP,
        transform=lambda value: str(value).strip(),
    )
    _copy_present_fields(
        source=body,
        target=custom,
        field_map=CUSTOM_UPPER_STRIP_FIELD_MAP,
        transform=lambda value: str(value).strip().upper(),
    )

    gitpeg_module_candidates = getattr(body, "gitpegModuleCandidates", None)
    if gitpeg_module_candidates is not None:
        custom["gitpeg_module_candidates"] = [
            str(item).strip()
            for item in gitpeg_module_candidates
            if str(item).strip()
        ]
    permission_matrix = getattr(body, "permissionMatrix", None)
    if permission_matrix is not None:
        custom["permission_matrix"] = _normalize_permission_matrix(permission_matrix)

    updates["custom_fields"] = custom

    res = sb.table("enterprise_configs").update(updates).eq("enterprise_id", enterprise_id).execute()
    if not res.data:
        raise HTTPException(500, "failed to update settings")

    latest = res.data[0]
    return _to_payload(latest, ent_data)


__all__ = [
    "get_settings_flow",
    "upload_template_flow",
    "update_settings_flow",
]

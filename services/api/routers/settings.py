"""
Enterprise settings routes for QCSpec.
"""

from __future__ import annotations

import os
import time
from functools import lru_cache
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

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
    key = str(
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    ).strip()
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
    gitpegRegistrarBaseUrl: Optional[str] = None
    gitpegPartnerCode: Optional[str] = None
    gitpegIndustryCode: Optional[str] = None
    gitpegClientId: Optional[str] = None
    gitpegClientSecret: Optional[str] = None
    gitpegRegistrationMode: Optional[str] = None
    gitpegReturnUrl: Optional[str] = None
    gitpegWebhookUrl: Optional[str] = None
    gitpegWebhookSecret: Optional[str] = None
    gitpegModuleCandidates: Optional[list[str]] = None
    erpnextSync: Optional[bool] = None
    erpnextUrl: Optional[str] = None
    erpnextSiteName: Optional[str] = None
    erpnextApiKey: Optional[str] = None
    erpnextApiSecret: Optional[str] = None
    erpnextUsername: Optional[str] = None
    erpnextPassword: Optional[str] = None
    erpnextProjectDoctype: Optional[str] = None
    erpnextProjectLookupField: Optional[str] = None
    erpnextProjectLookupValue: Optional[str] = None
    erpnextGitpegProjectUriField: Optional[str] = None
    erpnextGitpegSiteUriField: Optional[str] = None
    erpnextGitpegStatusField: Optional[str] = None
    erpnextGitpegResultJsonField: Optional[str] = None
    erpnextGitpegRegistrationIdField: Optional[str] = None
    erpnextGitpegNodeUriField: Optional[str] = None
    erpnextGitpegShellUriField: Optional[str] = None
    erpnextGitpegProofHashField: Optional[str] = None
    erpnextGitpegIndustryProfileIdField: Optional[str] = None
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


class GitPegRegistrarTestRequest(BaseModel):
    baseUrl: str
    partnerCode: str
    industryCode: str
    clientId: Optional[str] = None
    clientSecret: Optional[str] = None
    registrationMode: Optional[str] = "DOMAIN"
    returnUrl: Optional[str] = None
    webhookUrl: Optional[str] = None
    moduleCandidates: Optional[list[str]] = None
    timeoutMs: Optional[int] = 10000


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


def _should_trust_env_for_url(url: str) -> bool:
    host = str(urlparse(url).hostname or "").strip().lower()
    if not host:
        return True
    if host in {"localhost", "127.0.0.1", "::1"}:
        return False
    if host.endswith(".localhost"):
        return False
    return True


def _rewrite_localhost_alias_url(url: str) -> str:
    parsed = urlparse(url)
    host = str(parsed.hostname or "").strip().lower()
    if not host or not host.endswith(".localhost"):
        return url

    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth = f"{auth}:{parsed.password}"
        auth = f"{auth}@"
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{auth}127.0.0.1{port}"
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def _normalize_gitpeg_base_url(raw: Optional[str]) -> str:
    value = str(raw or "").strip().rstrip("/")
    if not value:
        raise HTTPException(400, "GitPeg base_url is required")
    if not value.startswith("http://") and not value.startswith("https://"):
        raise HTTPException(400, "GitPeg base_url must start with http:// or https://")
    return value


def _normalize_gitpeg_registration_mode(raw: Optional[str]) -> str:
    mode = str(raw or "DOMAIN").strip().upper()
    return mode if mode in {"DOMAIN", "SHELL"} else "DOMAIN"


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
    parsed = urlparse(url)
    host = str(parsed.hostname or "").strip()
    site_name = str(body.siteName or "").strip() or None
    if not site_name and host.endswith(".localhost"):
        site_name = host
    request_url = _rewrite_localhost_alias_url(url)
    username = str(body.username or "").strip()
    password = str(body.password or "").strip()
    timeout_ms = int(body.timeoutMs or 8000)
    timeout_s = min(max(timeout_ms / 1000, 2.0), 30.0)

    headers = _erp_headers(site_name)
    health_url = f"{request_url}/api/method/frappe.auth.get_logged_user"
    errors: list[str] = []
    started_at = time.perf_counter()

    async with httpx.AsyncClient(
        timeout=timeout_s,
        follow_redirects=True,
        trust_env=_should_trust_env_for_url(request_url),
    ) as client:
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
                    f"{request_url}/api/method/login",
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


@router.post("/gitpeg/test")
async def test_gitpeg_registrar_connection(body: GitPegRegistrarTestRequest):
    base_url = _normalize_gitpeg_base_url(body.baseUrl)
    partner_code = str(body.partnerCode or "").strip()
    industry_code = str(body.industryCode or "").strip()
    client_id = str(body.clientId or "").strip()
    client_secret = str(body.clientSecret or "").strip()
    if not partner_code or not industry_code:
        raise HTTPException(400, "partner_code and industry_code are required")
    if not client_id or not client_secret:
        raise HTTPException(400, "client_id and client_secret are required")

    timeout_ms = int(body.timeoutMs or 10000)
    timeout_s = min(max(timeout_ms / 1000, 2.0), 30.0)
    mode = _normalize_gitpeg_registration_mode(body.registrationMode)
    return_url = str(body.returnUrl or "").strip() or None
    webhook_url = str(body.webhookUrl or "").strip() or None
    modules = [str(item).strip() for item in (body.moduleCandidates or []) if str(item).strip()]
    if not modules:
        modules = ["proof", "utrip", "openapi"]

    session_body: dict[str, Any] = {
        "partner_code": partner_code,
        "industry_code": industry_code,
        "registration_mode": mode,
        "prefill_data": {
            "organization_name": "QCSpec Verify",
            "domain": "qcspec-verify.local",
        },
        "module_candidates": modules,
        "external_reference": f"qcspec-verify-{int(time.time())}",
    }
    if return_url:
        session_body["return_url"] = return_url
    if webhook_url:
        session_body["webhook_url"] = webhook_url

    create_endpoint = f"{base_url}/api/v1/partner/registration-sessions"
    exchange_endpoint = f"{base_url}/api/v1/partner/token/exchange"
    warnings: list[str] = []

    def _detail_from_response(res: httpx.Response) -> str:
        try:
            payload = res.json()
            if isinstance(payload, dict):
                msg = payload.get("detail") or payload.get("error") or payload.get("message")
                if msg:
                    return str(msg)
            return str(payload)
        except Exception:
            return (res.text or "").strip()

    try:
        async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
            create_res = await client.post(create_endpoint, json=session_body, headers={"Content-Type": "application/json"})
            create_payload: dict[str, Any] = {}

            if create_res.status_code >= 400:
                create_detail = _detail_from_response(create_res)
                low = create_detail.lower()
                if (
                    return_url
                    and create_res.status_code in {400, 422}
                    and "return_url" in low
                    and "not allowed" in low
                ):
                    retry_body = dict(session_body)
                    retry_body.pop("return_url", None)
                    retry_res = await client.post(
                        create_endpoint,
                        json=retry_body,
                        headers={"Content-Type": "application/json"},
                    )
                    if retry_res.status_code < 400:
                        warnings.append("return_url not allowed for partner; used fallback without return_url")
                        create_payload = retry_res.json() if retry_res.content else {}
                    else:
                        retry_detail = _detail_from_response(retry_res)
                        raise HTTPException(
                            502,
                            f"gitpeg session verify failed ({retry_res.status_code}): {retry_detail[:300]}",
                        )
                else:
                    raise HTTPException(
                        502,
                        f"gitpeg session verify failed ({create_res.status_code}): {create_detail[:300]}",
                    )
            else:
                create_payload = create_res.json() if create_res.content else {}

            if not isinstance(create_payload, dict):
                create_payload = {}

            # Optional probe for client_id/client_secret path.
            probe_status: Optional[int] = None
            probe_result = "not_executed"
            probe_detail = ""
            try:
                probe_res = await client.post(
                    exchange_endpoint,
                    json={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "code": "qcspec_verify_invalid_code",
                    },
                    headers={"Content-Type": "application/json"},
                )
                probe_status = probe_res.status_code
                probe_detail = _detail_from_response(probe_res)[:200]
                if probe_res.status_code in {400, 404}:
                    probe_result = "reachable_invalid_code"
                elif probe_res.status_code in {401, 403}:
                    probe_result = "credentials_rejected"
                elif probe_res.status_code < 300:
                    probe_result = "unexpected_success"
                elif probe_res.status_code >= 500:
                    probe_result = "server_error"
                else:
                    probe_result = "reachable_other_error"
            except Exception as exc:
                probe_result = "probe_error"
                probe_detail = str(exc)

            return {
                "ok": True,
                "message": "GitPeg Registrar connection successful",
                "base_url": base_url,
                "session_id": create_payload.get("session_id"),
                "hosted_register_url": create_payload.get("hosted_register_url"),
                "expires_at": create_payload.get("expires_at"),
                "warnings": warnings,
                "token_exchange_probe": {
                    "result": probe_result,
                    "status_code": probe_status,
                    "detail": probe_detail,
                },
            }
    except HTTPException:
        raise
    except httpx.TimeoutException as exc:
        raise HTTPException(504, f"gitpeg verify timeout: {exc.__class__.__name__}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"gitpeg verify network error: {exc.__class__.__name__}") from exc


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

"""
Connection test flows for enterprise settings.
"""

from __future__ import annotations

import time
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

import httpx
from fastapi import HTTPException


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


async def test_erpnext_connection_flow(*, body: Any) -> dict[str, Any]:
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


async def test_gitpeg_registrar_connection_flow(*, body: Any) -> dict[str, Any]:
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

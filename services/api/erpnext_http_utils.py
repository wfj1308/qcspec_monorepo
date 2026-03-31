"""
HTTP/auth transport helpers for ERPNext integration.
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

import httpx


def normalize_erp_url(raw: Optional[str]) -> str:
    value = str(raw or "").strip().rstrip("/")
    if not value:
        return ""
    if not value.startswith("http://") and not value.startswith("https://"):
        value = f"http://{value}"
    parsed = urlparse(value)
    # Users often paste Desk URL like https://host/app.
    # API base must be site root: https://host
    path = str(parsed.path or "").strip()
    if path in {"/app", "/desk"}:
        parsed = parsed._replace(path="")
        value = urlunparse(parsed).rstrip("/")
    return value


def erp_should_trust_env(url: str) -> bool:
    host = str(urlparse(url).hostname or "").strip().lower()
    if not host:
        return True
    if host in {"localhost", "127.0.0.1", "::1"}:
        return False
    if host.endswith(".localhost"):
        return False
    return True


def rewrite_localhost_alias_url(url: str) -> str:
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


def erp_headers(site_name: Optional[str], auth_header: Optional[str], *, as_json: bool = True) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "QCSpec-ERPNext-Bridge/1.0",
    }
    if as_json:
        headers["Content-Type"] = "application/json"
    site = str(site_name or "").strip()
    if site:
        headers["Host"] = site
        headers["X-Forwarded-Host"] = site
        headers["X-Frappe-Site-Name"] = site
    if auth_header:
        headers["Authorization"] = auth_header
    return headers


def erp_auth_candidates(api_key: Optional[str], api_secret: Optional[str]) -> list[tuple[str, str]]:
    key = str(api_key or "").strip()
    secret = str(api_secret or "").strip()
    out: list[tuple[str, str]] = []
    if key and secret:
        out.append(("token", f"token {key}:{secret}"))
    elif key:
        low = key.lower()
        if low.startswith("token "):
            out.append(("token", key))
        elif low.startswith("bearer "):
            out.append(("bearer", key))
        elif ":" in key:
            out.append(("token", f"token {key}"))
        else:
            out.append(("bearer", f"Bearer {key}"))
    return out


def erp_endpoint(base_url: str, path: str) -> str:
    raw = str(path or "").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if not raw.startswith("/"):
        raw = f"/{raw}"
    return f"{base_url}{raw}"


def safe_json_or_text(res: httpx.Response) -> Any:
    try:
        return res.json()
    except Exception:
        return (res.text or "").strip()


async def erp_request(
    custom: dict[str, Any],
    *,
    method: str,
    path: str,
    params: Optional[dict[str, Any]] = None,
    body: Optional[dict[str, Any]] = None,
    timeout_s: float = 10.0,
) -> dict[str, Any]:
    base_url = normalize_erp_url(custom.get("erpnext_url"))
    if not base_url:
        return {"attempted": False, "success": False, "reason": "erpnext_url_not_configured"}

    base_host = str(urlparse(base_url).hostname or "").strip()
    site_name = str(custom.get("erpnext_site_name") or "").strip() or None
    if not site_name and base_host.endswith(".localhost"):
        site_name = base_host
    site_candidates: list[Optional[str]] = [None]
    if site_name:
        site_candidates.append(site_name)

    request_base_url = rewrite_localhost_alias_url(base_url)
    endpoint = erp_endpoint(request_base_url, path)
    auth_candidates = erp_auth_candidates(custom.get("erpnext_api_key"), custom.get("erpnext_api_secret"))
    session_user = str(custom.get("erpnext_username") or "").strip()
    session_pass = str(custom.get("erpnext_password") or "").strip()
    has_session = bool(session_user and session_pass)
    if not auth_candidates and not has_session:
        return {"attempted": False, "success": False, "reason": "erpnext_credentials_not_configured"}

    errors: list[str] = []
    async with httpx.AsyncClient(
        timeout=timeout_s,
        follow_redirects=True,
        trust_env=erp_should_trust_env(endpoint),
    ) as client:
        for site_name_try in site_candidates:
            site_tag = site_name_try or "site:auto"
            for mode, auth_header in auth_candidates:
                headers = erp_headers(site_name_try, auth_header, as_json=body is not None)
                try:
                    res = await client.request(
                        method.upper(),
                        endpoint,
                        headers=headers,
                        params=params,
                        json=body if body is not None else None,
                    )
                    if res.status_code < 400:
                        return {
                            "attempted": True,
                            "success": True,
                            "authMode": mode,
                            "statusCode": res.status_code,
                            "data": safe_json_or_text(res),
                        }
                    detail = safe_json_or_text(res)
                    errors.append(f"{site_tag}:{mode}:{res.status_code}:{detail}")
                except Exception as exc:
                    errors.append(f"{site_tag}:{mode}:{exc.__class__.__name__}")

            if has_session:
                try:
                    login = await client.post(
                        f"{request_base_url}/api/method/login",
                        headers=erp_headers(site_name_try, None, as_json=False),
                        data={"usr": session_user, "pwd": session_pass},
                    )
                    if login.status_code >= 400:
                        errors.append(f"{site_tag}:session_login:{login.status_code}:{safe_json_or_text(login)}")
                    else:
                        headers = erp_headers(site_name_try, None, as_json=body is not None)
                        csrf = str(
                            login.headers.get("x-frappe-csrf-token")
                            or login.headers.get("X-Frappe-CSRF-Token")
                            or ""
                        ).strip()
                        if csrf:
                            headers["X-Frappe-CSRF-Token"] = csrf
                        res = await client.request(
                            method.upper(),
                            endpoint,
                            headers=headers,
                            params=params,
                            json=body if body is not None else None,
                        )
                        if res.status_code < 400:
                            return {
                                "attempted": True,
                                "success": True,
                                "authMode": "session",
                                "statusCode": res.status_code,
                                "data": safe_json_or_text(res),
                            }
                        errors.append(f"{site_tag}:session:{res.status_code}:{safe_json_or_text(res)}")
                except Exception as exc:
                    errors.append(f"{site_tag}:session:{exc.__class__.__name__}")

    return {"attempted": True, "success": False, "errors": errors}


def erp_request_sync(
    custom: dict[str, Any],
    *,
    method: str,
    path: str,
    params: Optional[dict[str, Any]] = None,
    body: Optional[dict[str, Any]] = None,
    timeout_s: float = 10.0,
) -> dict[str, Any]:
    base_url = normalize_erp_url(custom.get("erpnext_url"))
    if not base_url:
        return {"attempted": False, "success": False, "reason": "erpnext_url_not_configured"}

    base_host = str(urlparse(base_url).hostname or "").strip()
    site_name = str(custom.get("erpnext_site_name") or "").strip() or None
    if not site_name and base_host.endswith(".localhost"):
        site_name = base_host
    site_candidates: list[Optional[str]] = [None]
    if site_name:
        site_candidates.append(site_name)

    request_base_url = rewrite_localhost_alias_url(base_url)
    endpoint = erp_endpoint(request_base_url, path)
    auth_candidates = erp_auth_candidates(custom.get("erpnext_api_key"), custom.get("erpnext_api_secret"))
    session_user = str(custom.get("erpnext_username") or "").strip()
    session_pass = str(custom.get("erpnext_password") or "").strip()
    has_session = bool(session_user and session_pass)
    if not auth_candidates and not has_session:
        return {"attempted": False, "success": False, "reason": "erpnext_credentials_not_configured"}

    errors: list[str] = []
    with httpx.Client(
        timeout=timeout_s,
        follow_redirects=True,
        trust_env=erp_should_trust_env(endpoint),
    ) as client:
        for site_name_try in site_candidates:
            site_tag = site_name_try or "site:auto"
            for mode, auth_header in auth_candidates:
                headers = erp_headers(site_name_try, auth_header, as_json=body is not None)
                try:
                    res = client.request(
                        method.upper(),
                        endpoint,
                        headers=headers,
                        params=params,
                        json=body if body is not None else None,
                    )
                    if res.status_code < 400:
                        return {
                            "attempted": True,
                            "success": True,
                            "authMode": mode,
                            "statusCode": res.status_code,
                            "data": safe_json_or_text(res),
                        }
                    detail = safe_json_or_text(res)
                    errors.append(f"{site_tag}:{mode}:{res.status_code}:{detail}")
                except Exception as exc:
                    errors.append(f"{site_tag}:{mode}:{exc.__class__.__name__}")

            if has_session:
                try:
                    login = client.post(
                        f"{request_base_url}/api/method/login",
                        headers=erp_headers(site_name_try, None, as_json=False),
                        data={"usr": session_user, "pwd": session_pass},
                    )
                    if login.status_code >= 400:
                        errors.append(f"{site_tag}:session_login:{login.status_code}:{safe_json_or_text(login)}")
                    else:
                        headers = erp_headers(site_name_try, None, as_json=body is not None)
                        csrf = str(
                            login.headers.get("x-frappe-csrf-token")
                            or login.headers.get("X-Frappe-CSRF-Token")
                            or ""
                        ).strip()
                        if csrf:
                            headers["X-Frappe-CSRF-Token"] = csrf
                        res = client.request(
                            method.upper(),
                            endpoint,
                            headers=headers,
                            params=params,
                            json=body if body is not None else None,
                        )
                        if res.status_code < 400:
                            return {
                                "attempted": True,
                                "success": True,
                                "authMode": "session",
                                "statusCode": res.status_code,
                                "data": safe_json_or_text(res),
                            }
                        errors.append(f"{site_tag}:session:{res.status_code}:{safe_json_or_text(res)}")
                except Exception as exc:
                    errors.append(f"{site_tag}:session:{exc.__class__.__name__}")

    return {"attempted": True, "success": False, "errors": errors}

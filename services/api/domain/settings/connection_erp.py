"""ERPNext connection verification flow for enterprise settings."""

from __future__ import annotations

import time
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

import httpx
from fastapi import HTTPException
from services.api.domain.settings.connection_common import (
    body_field,
    body_text,
    clamp_timeout_seconds,
)


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


def _build_erp_success_payload(
    *,
    mode: str,
    url: str,
    site_name: Optional[str],
    user: str,
    started_at: float,
) -> dict[str, Any]:
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


async def _probe_erp_token_auth(
    *,
    client: httpx.AsyncClient,
    health_url: str,
    headers: dict[str, str],
    mode: str,
    auth_header: str,
) -> tuple[str, str]:
    req_headers = {**headers, "Authorization": auth_header}
    try:
        res = await client.get(health_url, headers=req_headers)
        if res.status_code >= 400:
            return "", f"{mode}:{res.status_code}"
        payload = res.json()
        return _extract_logged_user(payload), ""
    except httpx.TimeoutException:
        return "", f"{mode}:timeout"
    except Exception as exc:
        return "", f"{mode}:{str(exc)}"


async def _probe_erp_session_auth(
    *,
    client: httpx.AsyncClient,
    request_url: str,
    health_url: str,
    headers: dict[str, str],
    username: str,
    password: str,
) -> tuple[str, str]:
    try:
        login_res = await client.post(
            f"{request_url}/api/method/login",
            headers=headers,
            data={"usr": username, "pwd": password},
        )
        if login_res.status_code >= 400:
            return "", f"session_login:{login_res.status_code}"
        check_res = await client.get(health_url, headers=headers)
        if check_res.status_code >= 400:
            return "", f"session_check:{check_res.status_code}"
        payload = check_res.json()
        return _extract_logged_user(payload) or username, ""
    except httpx.TimeoutException:
        return "", "session:timeout"
    except Exception as exc:
        return "", f"session:{str(exc)}"


async def test_erpnext_connection_flow(*, body: Any) -> dict[str, Any]:
    url = _normalize_erp_url(body_text(body, "url"))
    parsed = urlparse(url)
    host = str(parsed.hostname or "").strip()
    site_name = body_text(body, "siteName") or None
    if not site_name and host.endswith(".localhost"):
        site_name = host
    request_url = _rewrite_localhost_alias_url(url)
    username = body_text(body, "username")
    password = body_text(body, "password")
    timeout_s = clamp_timeout_seconds(body_field(body, "timeoutMs"), default_ms=8000)

    headers = _erp_headers(site_name)
    health_url = f"{request_url}/api/method/frappe.auth.get_logged_user"
    errors: list[str] = []
    started_at = time.perf_counter()

    async with httpx.AsyncClient(
        timeout=timeout_s,
        follow_redirects=True,
        trust_env=_should_trust_env_for_url(request_url),
    ) as client:
        for mode, auth_header in _auth_candidates(
            body_text(body, "apiKey"),
            body_text(body, "apiSecret"),
        ):
            user, error = await _probe_erp_token_auth(
                client=client,
                health_url=health_url,
                headers=headers,
                mode=mode,
                auth_header=auth_header,
            )
            if error:
                errors.append(error)
                continue
            return _build_erp_success_payload(
                mode=mode,
                url=url,
                site_name=site_name,
                user=user,
                started_at=started_at,
            )

        if username and password:
            user, error = await _probe_erp_session_auth(
                client=client,
                request_url=request_url,
                health_url=health_url,
                headers=headers,
                username=username,
                password=password,
            )
            if error:
                errors.append(error)
            else:
                return _build_erp_success_payload(
                    mode="session",
                    url=url,
                    site_name=site_name,
                    user=user,
                    started_at=started_at,
                )

    detail = "; ".join(errors) if errors else "no valid auth info provided"
    raise HTTPException(502, f"failed to connect ERPNext ({detail})")


__all__ = [
    "test_erpnext_connection_flow",
]

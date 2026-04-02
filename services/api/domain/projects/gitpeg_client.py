"""Canonical projects GitPeg registrar client helpers."""

from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Callable, Optional
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

import httpx
from fastapi import HTTPException


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_registration_mode(value: Any) -> str:
    mode = str(value or "DOMAIN").strip().upper()
    return mode if mode in {"DOMAIN", "SHELL"} else "DOMAIN"


def _gitpeg_registrar_config(custom: dict[str, Any]) -> dict[str, Any]:
    modules = custom.get("gitpeg_module_candidates")
    if not isinstance(modules, list) or not modules:
        raw_modules = str(
            custom.get("gitpeg_module_candidates_csv")
            or os.getenv("GITPEG_MODULE_CANDIDATES")
            or "proof,utrip,openapi"
        ).strip()
        modules = [item.strip() for item in raw_modules.split(",") if item.strip()]

    base_url = str(
        custom.get("gitpeg_registrar_base_url")
        or os.getenv("GITPEG_REGISTRAR_BASE_URL")
        or "https://gitpeg.cn"
    ).strip().rstrip("/")

    return {
        "enabled": _to_bool(custom.get("gitpeg_enabled")),
        "base_url": base_url,
        "partner_code": str(
            custom.get("gitpeg_partner_code")
            or os.getenv("GITPEG_PARTNER_CODE")
            or ""
        ).strip(),
        "industry_code": str(
            custom.get("gitpeg_industry_code")
            or os.getenv("GITPEG_INDUSTRY_CODE")
            or ""
        ).strip(),
        "client_id": str(
            custom.get("gitpeg_client_id")
            or os.getenv("GITPEG_CLIENT_ID")
            or ""
        ).strip(),
        "client_secret": str(
            custom.get("gitpeg_client_secret")
            or custom.get("gitpeg_token")
            or os.getenv("GITPEG_CLIENT_SECRET")
            or ""
        ).strip(),
        "registration_mode": _normalize_registration_mode(
            custom.get("gitpeg_registration_mode")
            or os.getenv("GITPEG_REGISTRATION_MODE")
            or "DOMAIN"
        ),
        "return_url": str(
            custom.get("gitpeg_return_url")
            or os.getenv("GITPEG_RETURN_URL")
            or ""
        ).strip(),
        "webhook_url": str(
            custom.get("gitpeg_webhook_url")
            or os.getenv("GITPEG_WEBHOOK_URL")
            or ""
        ).strip(),
        "webhook_secret": str(
            custom.get("gitpeg_webhook_secret")
            or os.getenv("GITPEG_WEBHOOK_SECRET")
            or ""
        ).strip(),
        "modules": modules,
        "timeout_s": 15.0,
    }


def _append_query_params(url: str, params: dict[str, Any]) -> str:
    raw = str(url or "").strip()
    if not raw:
        return raw
    parsed = urlparse(raw)
    existing = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        k = str(key or "").strip()
        v = str(value or "").strip()
        if not k or not v:
            continue
        existing.setdefault(k, v)
    next_query = urlencode(existing, doseq=True)
    return urlunparse(parsed._replace(query=next_query))


def _gitpeg_registrar_ready(cfg: dict[str, Any]) -> bool:
    return all(
        [
            cfg.get("base_url"),
            cfg.get("partner_code"),
            cfg.get("industry_code"),
            cfg.get("client_id"),
            cfg.get("client_secret"),
        ]
    )


def _timeout_seconds(value: Any, *, default: float = 15.0) -> float:
    try:
        timeout = float(value if value is not None else default)
    except Exception:
        timeout = default
    if not math.isfinite(timeout) or timeout <= 0:
        timeout = default
    return min(max(timeout, 2.0), 30.0)


async def _gitpeg_create_registration_session(
    cfg: dict[str, Any],
    *,
    project: dict[str, Any],
    enterprise: dict[str, Any],
    slugify_fn: Optional[Callable[[str], str]] = None,
) -> dict[str, Any]:
    if not _gitpeg_registrar_ready(cfg):
        raise HTTPException(400, "gitpeg registrar config incomplete")

    project_name = str(project.get("name") or "").strip() or "project"
    if slugify_fn:
        slug = str(slugify_fn(project_name) or "").strip()
    else:
        raw = str(project_name or "").strip().lower()
        compact = re.sub(r"\s+", "", raw, flags=re.UNICODE)
        slug = re.sub(r"[^\w-]+", "", compact, flags=re.UNICODE)[:20] or "project"
    prefill_domain = f"{slug or 'project'}.local"
    body: dict[str, Any] = {
        "partner_code": cfg["partner_code"],
        "industry_code": cfg["industry_code"],
        "registration_mode": cfg["registration_mode"] or "DOMAIN",
        "prefill_data": {
            "organization_name": str(enterprise.get("name") or project.get("owner_unit") or project_name).strip(),
            "domain": prefill_domain,
        },
        "module_candidates": cfg.get("modules") or ["proof", "utrip", "openapi"],
        "external_reference": f"qcspec-proj-{project.get('id')}",
    }
    if cfg.get("return_url"):
        body["return_url"] = _append_query_params(
            cfg["return_url"],
            {
                "project_id": project.get("id"),
                "enterprise_id": project.get("enterprise_id") or enterprise.get("id"),
            },
        )
    if cfg.get("webhook_url"):
        body["webhook_url"] = cfg["webhook_url"]

    endpoint = f"{cfg['base_url']}/api/v1/partner/registration-sessions"
    timeout_s = _timeout_seconds(cfg.get("timeout_s"), default=15.0)
    try:
        async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
            res = await client.post(endpoint, json=body, headers={"Content-Type": "application/json"})
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"gitpeg session create failed (network): {exc.__class__.__name__}") from exc
    if res.status_code >= 400:
        detail = ""
        try:
            detail = json.dumps(res.json(), ensure_ascii=False)
        except Exception:
            detail = res.text
        raise HTTPException(502, f"gitpeg session create failed ({res.status_code}): {detail[:300]}")
    payload = res.json() if res.content else {}
    return payload if isinstance(payload, dict) else {}


async def _gitpeg_exchange_token(cfg: dict[str, Any], code: str) -> dict[str, Any]:
    endpoint = f"{cfg['base_url']}/api/v1/partner/token/exchange"
    timeout_s = _timeout_seconds(cfg.get("timeout_s"), default=15.0)
    body = {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "code": code,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
            res = await client.post(endpoint, json=body, headers={"Content-Type": "application/json"})
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"gitpeg token exchange failed (network): {exc.__class__.__name__}") from exc
    if res.status_code >= 400:
        detail = ""
        try:
            detail = json.dumps(res.json(), ensure_ascii=False)
        except Exception:
            detail = res.text
        raise HTTPException(502, f"gitpeg token exchange failed ({res.status_code}): {detail[:300]}")
    payload = res.json() if res.content else {}
    if not isinstance(payload, dict):
        raise HTTPException(502, "gitpeg token exchange returned invalid payload")
    return payload


async def _gitpeg_get_registration_result(cfg: dict[str, Any], access_token: str, registration_id: str) -> dict[str, Any]:
    reg_id = str(registration_id or "").strip()
    if not reg_id:
        raise HTTPException(400, "registration_id is required")

    endpoint = f"{cfg['base_url']}/api/v1/registrations/{quote(reg_id, safe='')}/result"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    timeout_s = _timeout_seconds(cfg.get("timeout_s"), default=15.0)
    try:
        async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
            res = await client.get(endpoint, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"gitpeg registration result failed (network): {exc.__class__.__name__}") from exc
    if res.status_code >= 400:
        detail = ""
        try:
            detail = json.dumps(res.json(), ensure_ascii=False)
        except Exception:
            detail = res.text
        raise HTTPException(502, f"gitpeg registration result failed ({res.status_code}): {detail[:300]}")
    payload = res.json() if res.content else {}
    if not isinstance(payload, dict):
        raise HTTPException(502, "gitpeg registration result returned invalid payload")
    return payload


async def _gitpeg_get_registration_session(
    cfg: dict[str, Any],
    session_id: str,
    *,
    access_token: Optional[str] = None,
) -> dict[str, Any]:
    sid = str(session_id or "").strip()
    if not sid:
        return {}

    endpoint = f"{cfg['base_url']}/api/v1/registration-sessions/{quote(sid, safe='')}"
    headers = {"Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    timeout_s = _timeout_seconds(cfg.get("timeout_s"), default=15.0)

    try:
        async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
            res = await client.get(endpoint, headers=headers)
    except httpx.HTTPError:
        return {}
    if res.status_code >= 400:
        return {}
    payload = res.json() if res.content else {}
    return payload if isinstance(payload, dict) else {}


to_bool = _to_bool
normalize_registration_mode = _normalize_registration_mode
gitpeg_registrar_config = _gitpeg_registrar_config
append_query_params = _append_query_params
gitpeg_registrar_ready = _gitpeg_registrar_ready
gitpeg_create_registration_session = _gitpeg_create_registration_session
gitpeg_exchange_token = _gitpeg_exchange_token
gitpeg_get_registration_result = _gitpeg_get_registration_result
gitpeg_get_registration_session = _gitpeg_get_registration_session


__all__ = [
    "to_bool",
    "normalize_registration_mode",
    "gitpeg_registrar_config",
    "append_query_params",
    "gitpeg_registrar_ready",
    "gitpeg_create_registration_session",
    "gitpeg_exchange_token",
    "gitpeg_get_registration_result",
    "gitpeg_get_registration_session",
    "_to_bool",
    "_normalize_registration_mode",
    "_gitpeg_registrar_config",
    "_append_query_params",
    "_gitpeg_registrar_ready",
    "_gitpeg_create_registration_session",
    "_gitpeg_exchange_token",
    "_gitpeg_get_registration_result",
    "_gitpeg_get_registration_session",
]

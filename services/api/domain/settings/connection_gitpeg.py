"""GitPeg Registrar connection verification flow for enterprise settings."""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx
from fastapi import HTTPException
from services.api.domain.settings.connection_common import (
    body_field,
    body_text,
    clamp_timeout_seconds,
)


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


def _classify_gitpeg_probe_status(status_code: int) -> str:
    if status_code in {400, 404}:
        return "reachable_invalid_code"
    if status_code in {401, 403}:
        return "credentials_rejected"
    if status_code < 300:
        return "unexpected_success"
    if status_code >= 500:
        return "server_error"
    return "reachable_other_error"


def _normalize_gitpeg_module_candidates(raw_modules: Any) -> list[str]:
    modules = [str(item).strip() for item in (raw_modules or []) if str(item).strip()]
    return modules or ["proof", "utrip", "openapi"]


def _build_gitpeg_session_body(
    *,
    partner_code: str,
    industry_code: str,
    mode: str,
    modules: list[str],
    return_url: Optional[str],
    webhook_url: Optional[str],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
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
        payload["return_url"] = return_url
    if webhook_url:
        payload["webhook_url"] = webhook_url
    return payload


def _build_gitpeg_success_payload(
    *,
    base_url: str,
    create_payload: dict[str, Any],
    warnings: list[str],
    token_exchange_probe: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ok": True,
        "message": "GitPeg Registrar connection successful",
        "base_url": base_url,
        "session_id": create_payload.get("session_id"),
        "hosted_register_url": create_payload.get("hosted_register_url"),
        "expires_at": create_payload.get("expires_at"),
        "warnings": warnings,
        "token_exchange_probe": token_exchange_probe,
    }


def _validate_gitpeg_required_fields(
    *,
    partner_code: str,
    industry_code: str,
    client_id: str,
    client_secret: str,
) -> None:
    if not partner_code or not industry_code:
        raise HTTPException(400, "partner_code and industry_code are required")
    if not client_id or not client_secret:
        raise HTTPException(400, "client_id and client_secret are required")


def _build_gitpeg_endpoints(base_url: str) -> tuple[str, str]:
    return (
        f"{base_url}/api/v1/partner/registration-sessions",
        f"{base_url}/api/v1/partner/token/exchange",
    )


async def _create_gitpeg_registration_session(
    *,
    client: httpx.AsyncClient,
    create_endpoint: str,
    session_body: dict[str, Any],
    return_url: Optional[str],
    warnings: list[str],
) -> dict[str, Any]:
    create_res = await client.post(create_endpoint, json=session_body, headers={"Content-Type": "application/json"})
    if create_res.status_code < 400:
        payload = create_res.json() if create_res.content else {}
        return payload if isinstance(payload, dict) else {}

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
            payload = retry_res.json() if retry_res.content else {}
            return payload if isinstance(payload, dict) else {}
        retry_detail = _detail_from_response(retry_res)
        raise HTTPException(
            502,
            f"gitpeg session verify failed ({retry_res.status_code}): {retry_detail[:300]}",
        )

    raise HTTPException(
        502,
        f"gitpeg session verify failed ({create_res.status_code}): {create_detail[:300]}",
    )


async def _probe_gitpeg_token_exchange(
    *,
    client: httpx.AsyncClient,
    exchange_endpoint: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
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
        probe_result = _classify_gitpeg_probe_status(probe_res.status_code)
    except Exception as exc:
        probe_result = "probe_error"
        probe_detail = str(exc)
    return {
        "result": probe_result,
        "status_code": probe_status,
        "detail": probe_detail,
    }


async def test_gitpeg_registrar_connection_flow(*, body: Any) -> dict[str, Any]:
    base_url = _normalize_gitpeg_base_url(body_text(body, "baseUrl"))
    partner_code = body_text(body, "partnerCode")
    industry_code = body_text(body, "industryCode")
    client_id = body_text(body, "clientId")
    client_secret = body_text(body, "clientSecret")
    _validate_gitpeg_required_fields(
        partner_code=partner_code,
        industry_code=industry_code,
        client_id=client_id,
        client_secret=client_secret,
    )

    timeout_s = clamp_timeout_seconds(body_field(body, "timeoutMs"), default_ms=10000)
    mode = _normalize_gitpeg_registration_mode(body_field(body, "registrationMode"))
    return_url = body_text(body, "returnUrl") or None
    webhook_url = body_text(body, "webhookUrl") or None
    modules = _normalize_gitpeg_module_candidates(body_field(body, "moduleCandidates"))
    session_body = _build_gitpeg_session_body(
        partner_code=partner_code,
        industry_code=industry_code,
        mode=mode,
        modules=modules,
        return_url=return_url,
        webhook_url=webhook_url,
    )

    create_endpoint, exchange_endpoint = _build_gitpeg_endpoints(base_url)
    warnings: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
            create_payload = await _create_gitpeg_registration_session(
                client=client,
                create_endpoint=create_endpoint,
                session_body=session_body,
                return_url=return_url,
                warnings=warnings,
            )
            token_exchange_probe = await _probe_gitpeg_token_exchange(
                client=client,
                exchange_endpoint=exchange_endpoint,
                client_id=client_id,
                client_secret=client_secret,
            )

            return _build_gitpeg_success_payload(
                base_url=base_url,
                create_payload=create_payload,
                warnings=warnings,
                token_exchange_probe=token_exchange_probe,
            )
    except HTTPException:
        raise
    except httpx.TimeoutException as exc:
        raise HTTPException(504, f"gitpeg verify timeout: {exc.__class__.__name__}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"gitpeg verify network error: {exc.__class__.__name__}") from exc


__all__ = [
    "test_gitpeg_registrar_connection_flow",
]

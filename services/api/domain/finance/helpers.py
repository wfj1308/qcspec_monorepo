"""Finance and audit flow helpers."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException
from supabase import Client

from services.api.domain.finance.payment_audit import (
    audit_trace,
    generate_payment_certificate,
    generate_railpact_instruction,
)

_DEFAULT_VERIFY_BASE_URL = "https://verify.qcspec.com"
_DEFAULT_CERT_EXECUTOR_URI = "v://executor/system/"
_DEFAULT_RAILPACT_EXECUTOR_URI = "v://executor/owner/system/"


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _require_text(value: Any, *, field: str) -> str:
    text = _to_text(value)
    if not text:
        raise HTTPException(400, f"{field} is required")
    return text


def _to_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _normalize_verify_base_url(value: Any) -> str:
    raw = _to_text(value, _DEFAULT_VERIFY_BASE_URL) or _DEFAULT_VERIFY_BASE_URL
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(400, "verify_base_url must be a valid http(s) URL")
    return raw.rstrip("/")


def generate_payment_certificate_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    project_uri = _require_text(getattr(body, "project_uri", ""), field="project_uri")
    period = _require_text(getattr(body, "period", ""), field="period")
    return generate_payment_certificate(
        sb=sb,
        project_uri=project_uri,
        period=period,
        project_name=_to_text(getattr(body, "project_name", "")),
        verify_base_url=_normalize_verify_base_url(getattr(body, "verify_base_url", _DEFAULT_VERIFY_BASE_URL)),
        create_proof=_to_bool(getattr(body, "create_proof", True), default=True),
        executor_uri=_to_text(getattr(body, "executor_uri", _DEFAULT_CERT_EXECUTOR_URI), _DEFAULT_CERT_EXECUTOR_URI),
        enforce_dual_pass=_to_bool(getattr(body, "enforce_dual_pass", True), default=True),
    )


def audit_trace_flow(
    *,
    payment_id: str,
    verify_base_url: str,
    sb: Client,
) -> dict[str, Any]:
    return audit_trace(
        sb=sb,
        payment_id=_require_text(payment_id, field="payment_id"),
        verify_base_url=_normalize_verify_base_url(verify_base_url),
    )


def generate_railpact_instruction_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return generate_railpact_instruction(
        sb=sb,
        payment_id=_require_text(getattr(body, "payment_id", ""), field="payment_id"),
        executor_uri=_to_text(
            getattr(body, "executor_uri", _DEFAULT_RAILPACT_EXECUTOR_URI),
            _DEFAULT_RAILPACT_EXECUTOR_URI,
        ),
        auto_submit=_to_bool(getattr(body, "auto_submit", False), default=False),
    )

"""Canonical finance-domain entry points for payment audit flows.

These wrappers keep domain callers decoupled from legacy module paths.
"""

from __future__ import annotations

from typing import Any

from services.api.domain.finance.integrations import (
    audit_trace,
    finalize_docfinal_delivery,
    generate_payment_certificate,
    generate_railpact_instruction,
)

__all__ = [
    "generate_payment_certificate",
    "audit_trace",
    "generate_railpact_instruction",
    "finalize_docfinal_delivery",
]


def generate_payment_certificate_flow(*, sb: Any, **kwargs: Any) -> dict[str, Any]:
    return generate_payment_certificate(sb=sb, **kwargs)


def payment_audit_trace_flow(*, sb: Any, **kwargs: Any) -> dict[str, Any]:
    return audit_trace(sb=sb, **kwargs)


def generate_railpact_instruction_flow(*, sb: Any, **kwargs: Any) -> dict[str, Any]:
    return generate_railpact_instruction(sb=sb, **kwargs)


def finalize_docfinal_delivery_flow(*, sb: Any, **kwargs: Any) -> dict[str, Any]:
    return finalize_docfinal_delivery(sb=sb, **kwargs)

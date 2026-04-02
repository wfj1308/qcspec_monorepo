"""Compatibility shim for legacy project ERP-writeback imports.

Prefer importing from ``services.api.domain.projects.erp_writeback`` directly.
"""

from __future__ import annotations

from services.api.domain.projects.erp_writeback import (
    _erp_auth_candidates,
    _erp_headers,
    _erp_lookup_docname,
    _erp_rewrite_localhost_alias,
    _erp_should_trust_env,
    _erp_writeback_autoreg,
    _normalize_erp_base_url,
)

__all__ = [
    "_erp_headers",
    "_erp_auth_candidates",
    "_erp_should_trust_env",
    "_erp_rewrite_localhost_alias",
    "_normalize_erp_base_url",
    "_erp_lookup_docname",
    "_erp_writeback_autoreg",
]

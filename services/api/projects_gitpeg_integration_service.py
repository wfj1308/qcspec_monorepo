"""Compatibility shim for legacy GitPeg integration imports.

Prefer importing from ``services.api.domain.projects.gitpeg_integration`` directly.
"""

from __future__ import annotations

from services.api.domain.projects.gitpeg_integration import (
    WEBHOOK_EVENT_WINDOW_S,
    WEBHOOK_TS_TOLERANCE_S,
    _event_seen_in_cache,
    _extract_gitpeg_callback_fields,
    _extract_project_id_from_external_reference,
    _find_value_recursive,
    _normalize_sig,
    _parse_db_ts,
    _parse_header_timestamp,
    _persist_gitpeg_activation,
    _register_webhook_event_once,
    _resolve_project_by_webhook_refs,
    _upsert_gitpeg_nodes,
    _upsert_project_registry_status,
    _verify_webhook_headers_and_signature,
)

__all__ = [
    "WEBHOOK_TS_TOLERANCE_S",
    "WEBHOOK_EVENT_WINDOW_S",
    "_extract_project_id_from_external_reference",
    "_find_value_recursive",
    "_extract_gitpeg_callback_fields",
    "_normalize_sig",
    "_parse_header_timestamp",
    "_parse_db_ts",
    "_event_seen_in_cache",
    "_verify_webhook_headers_and_signature",
    "_register_webhook_event_once",
    "_upsert_project_registry_status",
    "_upsert_gitpeg_nodes",
    "_persist_gitpeg_activation",
    "_resolve_project_by_webhook_refs",
]

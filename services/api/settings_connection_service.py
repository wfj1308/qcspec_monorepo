"""
Compatibility shim for legacy settings connection imports.

Prefer importing from ``services.api.domain.settings.connection`` directly.
"""

from __future__ import annotations

from services.api.domain.settings import connection as _settings_connection


def _ordered_unique(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


test_erpnext_connection_flow = _settings_connection.test_erpnext_connection_flow
test_gitpeg_registrar_connection_flow = _settings_connection.test_gitpeg_registrar_connection_flow

test_erpnext_connection = test_erpnext_connection_flow
test_gitpeg_registrar_connection = test_gitpeg_registrar_connection_flow

__all__ = _ordered_unique(
    [
        *_settings_connection.__all__,
        "test_erpnext_connection",
        "test_gitpeg_registrar_connection",
    ]
)

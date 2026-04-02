"""
Compatibility shim for legacy settings imports.

Prefer importing from:
- ``services.api.domain.settings.flows`` for CRUD settings flows
- ``services.api.domain.settings.connection`` for connection-test flows
"""

from __future__ import annotations

from services.api.domain.settings import SettingsService
from services.api.domain.settings import connection as _settings_connection
from services.api.domain.settings import flows as _settings_flows


def _ordered_unique(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


get_settings_flow = _settings_flows.get_settings_flow
upload_template_flow = _settings_flows.upload_template_flow
update_settings_flow = _settings_flows.update_settings_flow
test_erpnext_connection_flow = _settings_connection.test_erpnext_connection_flow
test_gitpeg_registrar_connection_flow = _settings_connection.test_gitpeg_registrar_connection_flow

get_settings = get_settings_flow
upload_template = upload_template_flow
update_settings = update_settings_flow
test_erpnext_connection = test_erpnext_connection_flow
test_gitpeg_registrar_connection = test_gitpeg_registrar_connection_flow

__all__ = _ordered_unique(
    [
        "SettingsService",
        *_settings_flows.__all__,
        *_settings_connection.__all__,
        "get_settings",
        "upload_template",
        "update_settings",
        "test_erpnext_connection",
        "test_gitpeg_registrar_connection",
    ]
)

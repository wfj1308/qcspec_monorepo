"""Compatibility shim for legacy settings helper imports.

Prefer importing from:
- ``services.api.domain.settings.flows`` for CRUD settings flows
- ``services.api.domain.settings.connection`` for connection-test flows
"""

from __future__ import annotations

from services.api.domain.settings.connection import (
    test_erpnext_connection_flow,
    test_gitpeg_registrar_connection_flow,
)
from services.api.domain.settings.flows import (
    get_settings_flow,
    update_settings_flow,
    upload_template_flow,
)

get_settings = get_settings_flow
upload_template = upload_template_flow
update_settings = update_settings_flow
test_erpnext_connection = test_erpnext_connection_flow
test_gitpeg_registrar_connection = test_gitpeg_registrar_connection_flow


__all__ = [
    "get_settings_flow",
    "upload_template_flow",
    "update_settings_flow",
    "test_erpnext_connection_flow",
    "test_gitpeg_registrar_connection_flow",
    "get_settings",
    "upload_template",
    "update_settings",
    "test_erpnext_connection",
    "test_gitpeg_registrar_connection",
]

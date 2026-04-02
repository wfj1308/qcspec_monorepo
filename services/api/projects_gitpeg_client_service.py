"""Compatibility shim for legacy projects GitPeg client imports.

Prefer importing from ``services.api.domain.projects.gitpeg_client`` directly.
"""

from __future__ import annotations

from services.api.domain.projects import gitpeg_client as _gitpeg_client


def _ordered_unique(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


to_bool = _gitpeg_client.to_bool
normalize_registration_mode = _gitpeg_client.normalize_registration_mode
gitpeg_registrar_config = _gitpeg_client.gitpeg_registrar_config
append_query_params = _gitpeg_client.append_query_params
gitpeg_registrar_ready = _gitpeg_client.gitpeg_registrar_ready
gitpeg_create_registration_session = _gitpeg_client.gitpeg_create_registration_session
gitpeg_exchange_token = _gitpeg_client.gitpeg_exchange_token
gitpeg_get_registration_result = _gitpeg_client.gitpeg_get_registration_result
gitpeg_get_registration_session = _gitpeg_client.gitpeg_get_registration_session

_to_bool = _gitpeg_client._to_bool
_normalize_registration_mode = _gitpeg_client._normalize_registration_mode
_gitpeg_registrar_config = _gitpeg_client._gitpeg_registrar_config
_append_query_params = _gitpeg_client._append_query_params
_gitpeg_registrar_ready = _gitpeg_client._gitpeg_registrar_ready
_gitpeg_create_registration_session = _gitpeg_client._gitpeg_create_registration_session
_gitpeg_exchange_token = _gitpeg_client._gitpeg_exchange_token
_gitpeg_get_registration_result = _gitpeg_client._gitpeg_get_registration_result
_gitpeg_get_registration_session = _gitpeg_client._gitpeg_get_registration_session

# Additional compatibility aliases for older helper names.
create_registration_session = gitpeg_create_registration_session
exchange_token = gitpeg_exchange_token
get_registration_result = gitpeg_get_registration_result
get_registration_session = gitpeg_get_registration_session
registrar_config = gitpeg_registrar_config
registrar_ready = gitpeg_registrar_ready

_create_registration_session = _gitpeg_create_registration_session
_exchange_token = _gitpeg_exchange_token
_get_registration_result = _gitpeg_get_registration_result
_get_registration_session = _gitpeg_get_registration_session
_registrar_config = _gitpeg_registrar_config
_registrar_ready = _gitpeg_registrar_ready

__all__ = _ordered_unique(
    [
        *_gitpeg_client.__all__,
        "registrar_config",
        "registrar_ready",
        "create_registration_session",
        "exchange_token",
        "get_registration_result",
        "get_registration_session",
        "_registrar_config",
        "_registrar_ready",
        "_create_registration_session",
        "_exchange_token",
        "_get_registration_result",
        "_get_registration_session",
    ]
)

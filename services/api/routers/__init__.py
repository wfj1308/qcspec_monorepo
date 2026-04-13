"""Router registry for QCSpec API."""

from __future__ import annotations

from fastapi import Depends

from services.api.dependencies import require_auth_identity

from . import auth, dtorole_proxy, upload_proxy

AUTH_DEP = [Depends(require_auth_identity)]

ROUTER_REGISTRY = [
    {"router": auth.router, "prefix": "/v1/auth", "tags": ["auth"]},
    {"router": dtorole_proxy.router, "prefix": "/v1/dtorole", "tags": ["dtorole"], "dependencies": AUTH_DEP},
    {"router": dtorole_proxy.router, "prefix": "/api/v1/dtorole", "tags": ["dtorole-api"], "dependencies": AUTH_DEP},
    {"router": upload_proxy.router, "tags": ["upload-proxy"], "dependencies": AUTH_DEP},
]

__all__ = ["ROUTER_REGISTRY"]

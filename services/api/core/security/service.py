"""Security helpers for DID identity, DTORole guards, and URI validation."""

from __future__ import annotations

from typing import Any, Iterable

from fastapi import HTTPException

from services.api.core.base import BaseService


class DIDGuardService(BaseService):
    def validate_v_uri(self, value: str | None, *, field_name: str = "v_uri") -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        if text.startswith("v://") or text.startswith("http://") or text.startswith("https://"):
            return text
        raise HTTPException(status_code=400, detail=f"{field_name} must start with v:// or an allowed public URL")

    def require_roles(self, identity: dict[str, Any], allowed_roles: Iterable[str]) -> dict[str, Any]:
        allowed = {str(role).upper() for role in allowed_roles if str(role).strip()}
        current = str(identity.get("dto_role") or identity.get("role") or "PUBLIC").upper()
        if allowed and current not in allowed:
            raise HTTPException(status_code=403, detail=f"DTORole {current} is not allowed for this action")
        return identity

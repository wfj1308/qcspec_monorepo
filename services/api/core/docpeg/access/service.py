"""DocPeg execution gate backed by GitPeg registration tables.

This service enforces a simple rule:
all state-changing DocPeg operations must target registered sovereign nodes
and be executed by an authenticated identity with allowed DTORole.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from supabase import Client

from services.api.core.base import BaseService
from services.api.core.security import DIDGuardService

_ACTIVE_PROJECT_STATUSES = {"active", "verified", "enabled", "registered"}
_WRITE_ROLE_TOKENS = {
    "OWNER",
    "ADMIN",
    "SUPER_ADMIN",
    "SUPERADMIN",
    "MANAGER",
    "QA_MANAGER",
    "QCSPEC_ADMIN",
}


def _to_text(value: Any) -> str:
    return str(value or "").strip()


class DocPegExecutionGateService(BaseService):
    """GitPeg-backed access gate for DocPeg Core API execution."""

    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)
        self._did_guard = DIDGuardService()

    def enforce_execution(
        self,
        *,
        identity: dict[str, Any] | None,
        operation: str,
        access_mode: str = "write",
        project_uri: str = "",
        node_uri: str = "",
        actor_uri: str = "",
    ) -> dict[str, Any]:
        id_pack = identity if isinstance(identity, dict) else {}
        if not id_pack:
            raise HTTPException(status_code=401, detail="auth identity is required")

        normalized_project_uri = self._normalize_uri(project_uri, field_name="project_uri")
        normalized_node_uri = self._normalize_uri(node_uri, field_name="node_uri")
        normalized_actor_uri = self._normalize_uri(actor_uri, field_name="actor_uri")
        if not normalized_project_uri and not normalized_node_uri:
            raise HTTPException(status_code=400, detail="project_uri or node_uri is required")

        mode = _to_text(access_mode).lower() or "write"
        if mode == "write":
            self._require_write_role(id_pack, operation=operation)

        self._assert_actor_identity_consistency(identity=id_pack, actor_uri=normalized_actor_uri)

        project_registration: dict[str, Any] | None = None
        if normalized_project_uri:
            project_registration = self._resolve_project_registration(normalized_project_uri)
            if project_registration is None:
                raise HTTPException(
                    status_code=403,
                    detail=f"project_uri is not registered in GitPeg: {normalized_project_uri}",
                )
            project_status = _to_text(project_registration.get("gitpeg_status")).lower()
            if project_status and project_status not in _ACTIVE_PROJECT_STATUSES:
                raise HTTPException(
                    status_code=403,
                    detail=f"project_uri is not active in GitPeg: {normalized_project_uri} ({project_status})",
                )

        node_registration: dict[str, Any] | None = None
        if normalized_node_uri:
            node_registration = self._resolve_node_registration(normalized_node_uri)
            if node_registration is None and normalized_project_uri:
                if not self._uri_belongs_to_project(normalized_node_uri, normalized_project_uri):
                    raise HTTPException(
                        status_code=403,
                        detail=f"node_uri does not belong to project_uri: {normalized_node_uri}",
                    )
            elif node_registration is None and not normalized_project_uri:
                raise HTTPException(
                    status_code=403,
                    detail=f"node_uri is not registered in GitPeg: {normalized_node_uri}",
                )

        return {
            "ok": True,
            "operation": operation,
            "access_mode": mode,
            "project_uri": normalized_project_uri,
            "node_uri": normalized_node_uri,
            "actor_uri": normalized_actor_uri,
            "project_registration": project_registration or {},
            "node_registration": node_registration or {},
        }

    def _normalize_uri(self, value: Any, *, field_name: str) -> str:
        return _to_text(self._did_guard.validate_v_uri(_to_text(value), field_name=field_name))

    def _identity_roles(self, identity: dict[str, Any]) -> set[str]:
        roles: set[str] = set()
        dto_role = _to_text(identity.get("dto_role") or identity.get("role"))
        if dto_role:
            roles.add(dto_role.upper())
        raw_roles = identity.get("roles")
        if isinstance(raw_roles, (list, tuple, set)):
            for role in raw_roles:
                token = _to_text(role).upper()
                if token:
                    roles.add(token)
        return roles

    def _require_write_role(self, identity: dict[str, Any], *, operation: str) -> None:
        roles = self._identity_roles(identity)
        if roles.intersection(_WRITE_ROLE_TOKENS):
            return
        raise HTTPException(
            status_code=403,
            detail=f"operation {operation} requires elevated DTORole; current roles={sorted(roles)}",
        )

    def _assert_actor_identity_consistency(self, *, identity: dict[str, Any], actor_uri: str) -> None:
        if not actor_uri:
            return
        identity_uri = _to_text(identity.get("v_uri") or identity.get("identity_uri"))
        if not identity_uri:
            return
        actor = actor_uri.rstrip("/")
        ident = identity_uri.rstrip("/")
        if actor == ident:
            return
        raise HTTPException(status_code=403, detail="actor_uri does not match authenticated identity")

    def _resolve_project_registration(self, project_uri: str) -> dict[str, Any] | None:
        sb = self.require_supabase()
        candidate_uris = sorted({project_uri.rstrip("/"), project_uri.rstrip("/") + "/"})
        try:
            res = (
                sb.table("coord_gitpeg_project_registry")
                .select("project_uri,gitpeg_status,project_code,source_system")
                .in_("project_uri", candidate_uris)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"gitpeg project registry unavailable: {exc}") from exc
        rows = res.data or []
        for row in rows:
            if isinstance(row, dict):
                return row
        return None

    def _resolve_node_registration(self, node_uri: str) -> dict[str, Any] | None:
        sb = self.require_supabase()
        candidate_uris = sorted({node_uri.rstrip("/"), node_uri.rstrip("/") + "/"})
        try:
            res = (
                sb.table("coord_gitpeg_nodes")
                .select("uri,uri_type,project_code,namespace_uri")
                .in_("uri", candidate_uris)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"gitpeg node registry unavailable: {exc}") from exc
        rows = res.data or []
        for row in rows:
            if isinstance(row, dict):
                return row
        return None

    def _uri_belongs_to_project(self, node_uri: str, project_uri: str) -> bool:
        node = node_uri.rstrip("/") + "/"
        project = project_uri.rstrip("/") + "/"
        return node.startswith(project)


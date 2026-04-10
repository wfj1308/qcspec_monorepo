"""GitPeg autoreg flow helpers used by routers and domain services."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.domain.autoreg.flows import (
    AutoRegisterProjectRequest,
    autoreg_project_flow,
    autoreg_projects_flow,
    normalize_request,
    upsert_autoreg,
)


# Backward-compatible exports used by other modules.
_normalize_request = normalize_request
_upsert_autoreg = upsert_autoreg


async def autoreg_project(*, req: AutoRegisterProjectRequest, sb: Client) -> dict[str, Any]:
    return await autoreg_project_flow(req=req, sb=sb)


def autoreg_projects(
    *,
    limit: int,
    sb: Client,
    enterprise_id: str | None = None,
    namespace_uri: str | None = None,
) -> dict[str, Any]:
    return autoreg_projects_flow(
        limit=limit,
        sb=sb,
        enterprise_id=enterprise_id,
        namespace_uri=namespace_uri,
    )

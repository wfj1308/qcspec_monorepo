"""Inspection flow helpers used by routers and domain services."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.domain.inspections.flows import (
    create_inspection_flow,
    delete_inspection_flow,
    list_inspections_flow,
    project_stats_flow,
)


async def list_inspections(
    *,
    project_id: str,
    result: str | None,
    kind: str | None,
    limit: int,
    offset: int,
    sb: Client,
) -> dict[str, Any]:
    return await list_inspections_flow(
        project_id=project_id,
        result=result,
        kind=kind,
        limit=limit,
        offset=offset,
        sb=sb,
    )


async def create_inspection(*, body: Any, sb: Client) -> dict[str, Any]:
    return await create_inspection_flow(body=body, sb=sb)


async def project_stats(*, project_id: str, sb: Client) -> dict[str, Any]:
    return await project_stats_flow(project_id=project_id, sb=sb)


async def delete_inspection(*, inspection_id: str, sb: Client) -> dict[str, Any]:
    return await delete_inspection_flow(inspection_id=inspection_id, sb=sb)

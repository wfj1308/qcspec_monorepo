"""ERPNext integration flow helpers used by routers and domain services."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.domain.erpnext.flows import (
    check_metering_gate_flow,
    get_metering_requests_flow,
    get_project_basics_flow,
    notify_erpnext_flow,
    probe_erpnext_flow,
)


async def check_metering_gate(
    *,
    enterprise_id: str,
    stake: str,
    subitem: str,
    result: str,
    project_id: str | None,
    project_code: str | None,
    sb: Client,
) -> dict[str, Any]:
    return await check_metering_gate_flow(
        enterprise_id=enterprise_id,
        stake=stake,
        subitem=subitem,
        result=result,
        project_id=project_id,
        project_code=project_code,
        sb=sb,
    )


async def get_project_basics(
    *,
    enterprise_id: str,
    project_code: str | None,
    project_name: str | None,
    sb: Client,
) -> dict[str, Any]:
    return await get_project_basics_flow(
        enterprise_id=enterprise_id,
        project_code=project_code,
        project_name=project_name,
        sb=sb,
    )


async def get_metering_requests(
    *,
    enterprise_id: str,
    project_code: str | None,
    stake: str | None,
    subitem: str | None,
    status: str | None,
    sb: Client,
) -> dict[str, Any]:
    return await get_metering_requests_flow(
        enterprise_id=enterprise_id,
        project_code=project_code,
        stake=stake,
        subitem=subitem,
        status=status,
        sb=sb,
    )


async def notify_erpnext(*, body: Any, sb: Client) -> dict[str, Any]:
    return await notify_erpnext_flow(body=body, sb=sb)


async def probe_erpnext(
    *,
    enterprise_id: str,
    sample_project_name: str,
    sample_stake: str,
    sample_subitem: str,
    sb: Client,
) -> dict[str, Any]:
    return await probe_erpnext_flow(
        enterprise_id=enterprise_id,
        sample_project_name=sample_project_name,
        sample_stake=sample_stake,
        sample_subitem=sample_subitem,
        sb=sb,
    )

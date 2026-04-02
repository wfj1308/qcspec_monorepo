"""Public verify flow helpers used by routers and domain services."""

from __future__ import annotations

from typing import Any

from fastapi.responses import StreamingResponse
from supabase import Client

from services.api.domain.verify.flows import (
    download_dsp_package_flow,
    get_public_verify_detail_flow,
    resolve_normpeg_threshold_public_flow,
    resolve_spec_rule_public_flow,
    run_mock_anchor_once_flow,
)


async def resolve_spec_rule_public(
    *,
    spec_uri: str,
    metric: str,
    component_type: str,
    sb: Client,
) -> dict[str, Any]:
    return await resolve_spec_rule_public_flow(
        spec_uri=spec_uri,
        metric=metric,
        component_type=component_type,
        sb=sb,
    )


async def resolve_normpeg_threshold_public(
    *,
    spec_uri: str,
    context: str,
    value: float | None,
    design: float | None,
    sb: Client,
) -> dict[str, Any]:
    return await resolve_normpeg_threshold_public_flow(
        spec_uri=spec_uri,
        context=context,
        value=value,
        design=design,
        sb=sb,
    )


async def run_mock_anchor_once() -> dict[str, Any]:
    return await run_mock_anchor_once_flow()


async def get_public_verify_detail(
    *,
    proof_id: str,
    lineage_depth: str,
    verify_base_url: str,
    sb: Client,
) -> dict[str, Any]:
    return await get_public_verify_detail_flow(
        proof_id=proof_id,
        lineage_depth=lineage_depth,
        sb=sb,
        verify_base_url=verify_base_url,
    )


async def download_dsp_package(
    *,
    proof_id: str,
    verify_base_url: str,
    sb: Client,
) -> StreamingResponse:
    return await download_dsp_package_flow(
        proof_id=proof_id,
        sb=sb,
        verify_base_url=verify_base_url,
    )

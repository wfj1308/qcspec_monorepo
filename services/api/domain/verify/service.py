"""Public verify domain facade."""

from __future__ import annotations

from typing import Any

from fastapi.responses import StreamingResponse
from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.verify.helpers import (
    download_dsp_package,
    get_public_verify_detail,
    resolve_normpeg_threshold_public,
    resolve_spec_rule_public,
    run_mock_anchor_once,
)


class PublicVerifyService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def resolve_spec_rule_public(self, *, spec_uri: str, metric: str, component_type: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "resolve_spec_rule_public",
            resolve_spec_rule_public,
            spec_uri=spec_uri,
            metric=metric,
            component_type=component_type,
            sb=supabase,
        )

    async def resolve_normpeg_threshold_public(
        self,
        *,
        spec_uri: str,
        context: str,
        value: float | None,
        design: float | None,
    ) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "resolve_normpeg_threshold_public",
            resolve_normpeg_threshold_public,
            spec_uri=spec_uri,
            context=context,
            value=value,
            design=design,
            sb=supabase,
        )

    async def run_mock_anchor_once(self) -> dict[str, Any]:
        return await self.run_guarded("run_mock_anchor_once", run_mock_anchor_once)

    async def get_public_verify_detail(
        self,
        *,
        proof_id: str,
        lineage_depth: str,
        verify_base_url: str,
    ) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "get_public_verify_detail",
            get_public_verify_detail,
            proof_id=proof_id,
            lineage_depth=lineage_depth,
            verify_base_url=verify_base_url,
            sb=supabase,
        )

    async def download_dsp_package(
        self,
        *,
        proof_id: str,
        verify_base_url: str,
    ) -> StreamingResponse:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "download_dsp_package",
            download_dsp_package,
            proof_id=proof_id,
            verify_base_url=verify_base_url,
            sb=supabase,
        )

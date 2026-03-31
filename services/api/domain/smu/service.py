"""SMU and genesis import facade."""

from __future__ import annotations

from typing import Any

from fastapi.concurrency import run_in_threadpool
from services.api.core.base import BaseService
from services.api.proof_flow_service import (
    retry_erpnext_push_queue,
    smu_execute_flow,
    smu_freeze_flow,
    smu_genesis_import_active_job_flow,
    smu_genesis_import_async_flow,
    smu_genesis_import_flow,
    smu_genesis_import_job_flow,
    smu_genesis_preview_flow,
    smu_node_context_flow,
    smu_sign_flow,
    smu_spu_library_flow,
    smu_validate_logic_flow,
)


class SMUService(BaseService):
    async def import_genesis(self, **kwargs: Any) -> Any:
        return await self.run_guarded("smu_import_genesis", run_in_threadpool, smu_genesis_import_flow, **kwargs, sb=self.require_supabase())

    async def preview_genesis(self, **kwargs: Any) -> Any:
        return await self.run_guarded("smu_preview_genesis", run_in_threadpool, smu_genesis_preview_flow, **kwargs, sb=self.require_supabase())

    async def import_genesis_async(self, **kwargs: Any) -> Any:
        return await self.run_guarded("smu_import_genesis_async", smu_genesis_import_async_flow, **kwargs)

    async def get_import_job(self, *, job_id: str) -> Any:
        return await self.run_guarded("smu_import_job", smu_genesis_import_job_flow, job_id=job_id)

    async def get_active_import_job(self, *, project_uri: str) -> Any:
        return await self.run_guarded("smu_import_active_job", smu_genesis_import_active_job_flow, project_uri=project_uri)

    async def get_spu_library(self) -> Any:
        return await self.run_guarded("smu_spu_library", smu_spu_library_flow)

    async def get_node_context(self, **kwargs: Any) -> Any:
        return await self.run_guarded("smu_node_context", smu_node_context_flow, sb=self.require_supabase(), **kwargs)

    async def execute_trip(self, *, body: Any) -> Any:
        return await self.run_guarded("smu_execute", smu_execute_flow, body=body, sb=self.require_supabase())

    async def sign_trip(self, *, body: Any) -> Any:
        return await self.run_guarded("smu_sign", smu_sign_flow, body=body, sb=self.require_supabase())

    async def validate_logic(self, *, body: Any) -> Any:
        return await self.run_guarded("smu_validate_logic", smu_validate_logic_flow, body=body, sb=self.require_supabase())

    async def freeze_asset(self, *, body: Any) -> Any:
        return await self.run_guarded("smu_freeze", smu_freeze_flow, body=body, sb=self.require_supabase())

    async def retry_erpnext_push(self, *, limit: int) -> Any:
        return await self.run_guarded("smu_retry_erpnext_push", retry_erpnext_push_queue, sb=self.require_supabase(), limit=limit)

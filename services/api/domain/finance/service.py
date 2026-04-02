"""Finance/audit domain facade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.finance.helpers import (
    audit_trace_flow,
    generate_payment_certificate_flow,
    generate_railpact_instruction_flow,
)


class FinanceAuditService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def payment_certificate(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "generate_payment_certificate",
            generate_payment_certificate_flow,
            sb=supabase,
            body=body,
        )

    async def audit_trace(self, *, payment_id: str, verify_base_url: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "payment_audit_trace",
            audit_trace_flow,
            payment_id=payment_id,
            verify_base_url=verify_base_url,
            sb=supabase,
        )

    async def railpact_instruction(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "generate_railpact_instruction",
            generate_railpact_instruction_flow,
            sb=supabase,
            body=body,
        )

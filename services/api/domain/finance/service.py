"""Finance/audit domain façade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.boq_payment_audit_service import audit_trace, generate_payment_certificate, generate_railpact_instruction
from services.api.core.base import BaseService


class FinanceAuditService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def payment_certificate(self, *, body: Any) -> Any:
        return await self.run_guarded(
            "generate_payment_certificate",
            generate_payment_certificate,
            sb=self.require_supabase(),
            **body.model_dump(exclude_none=True),
        )

    async def audit_trace(self, *, payment_id: str, verify_base_url: str) -> Any:
        return await self.run_guarded(
            "payment_audit_trace",
            audit_trace,
            payment_id=payment_id,
            verify_base_url=verify_base_url,
            sb=self.require_supabase(),
        )

    async def railpact_instruction(self, *, body: Any) -> Any:
        return await self.run_guarded(
            "generate_railpact_instruction",
            generate_railpact_instruction,
            sb=self.require_supabase(),
            **body.model_dump(exclude_none=True),
        )

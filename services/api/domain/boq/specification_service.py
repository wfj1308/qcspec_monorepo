"""Specification and gate-editor domain facade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.boq.specification_helpers import (
    generate_gate_rules_via_ai_flow,
    get_gate_editor_payload_flow,
    import_gate_rules_from_norm_flow,
    rollback_gate_rule_version_flow,
    save_gate_rule_version_flow,
    save_spec_dict_flow,
)


class BOQSpecificationService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def gate_editor_payload(self, *, project_uri: str, subitem_code: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "get_gate_editor_payload",
            get_gate_editor_payload_flow,
            project_uri=project_uri,
            subitem_code=subitem_code,
            sb=supabase,
        )

    async def import_gate_rules_from_norm(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "import_gate_rules_from_norm",
            import_gate_rules_from_norm_flow,
            body=body,
            sb=supabase,
        )

    async def generate_gate_rules_via_ai(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "generate_gate_rules_via_ai",
            generate_gate_rules_via_ai_flow,
            body=body,
            sb=supabase,
        )

    async def save_gate_rule_version(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "save_gate_rule_version",
            save_gate_rule_version_flow,
            body=body,
            sb=supabase,
        )

    async def rollback_gate_rule_version(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "rollback_gate_rule_version",
            rollback_gate_rule_version_flow,
            body=body,
            sb=supabase,
        )

    async def save_spec_dict(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "save_spec_dict",
            save_spec_dict_flow,
            body=body,
            sb=supabase,
        )

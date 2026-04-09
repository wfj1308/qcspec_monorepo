"""SignPeg domain facade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.signpeg.helpers import (
    add_executor_requires_service_flow,
    add_org_member_service_flow,
    add_org_project_service_flow,
    check_tool_status_service_flow,
    add_executor_certificate_service_flow,
    add_executor_skill_service_flow,
    check_executor_certificate_expiry_service_flow,
    delegate_service_flow,
    explain_gate_service_flow,
    explain_process_service_flow,
    get_acceptance_service_flow,
    get_executor_by_id_service_flow,
    get_org_branches_service_flow,
    get_org_members_service_flow,
    get_executor_status_service_flow,
    import_executors_service_flow,
    list_executors_service_flow,
    get_executor_service_flow,
    register_executorpeg_service_flow,
    register_executor_service_flow,
    register_tool_service_flow,
    search_executors_service_flow,
    get_tool_service_flow,
    get_tool_status_service_flow,
    list_tools_service_flow,
    use_tool_service_flow,
    maintain_tool_service_flow,
    maintain_executor_service_flow,
    retire_tool_service_flow,
    sign_acceptance_condition_service_flow,
    submit_acceptance_service_flow,
    use_executor_service_flow,
    sign_service_flow,
    status_service_flow,
    update_executor_holder_service_flow,
    validate_field_service_flow,
    verify_service_flow,
)


class SignPegService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def register_executor(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("register_executor", register_executor_service_flow, sb=supabase, body=body)

    async def register_executorpeg(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("register_executorpeg", register_executorpeg_service_flow, sb=supabase, body=body)

    async def import_executors(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("import_executors", import_executors_service_flow, sb=supabase, body=body)

    async def get_executor(self, *, executor_uri: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_executor", get_executor_service_flow, sb=supabase, executor_uri=executor_uri)

    async def get_executor_by_id(self, *, executor_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_executor_by_id", get_executor_by_id_service_flow, sb=supabase, executor_id=executor_id)

    async def get_executor_status(self, *, executor_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_executor_status", get_executor_status_service_flow, sb=supabase, executor_id=executor_id)

    async def list_executors(self, *, org_uri: str = "") -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("list_executors", list_executors_service_flow, sb=supabase, org_uri=org_uri)

    async def search_executors(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("search_executors", search_executors_service_flow, sb=supabase, body=body)

    async def get_org_members(self, *, org_uri: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_org_members", get_org_members_service_flow, sb=supabase, org_uri=org_uri)

    async def get_org_branches(self, *, org_uri: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_org_branches", get_org_branches_service_flow, sb=supabase, org_uri=org_uri)

    async def add_org_member(self, *, org_uri: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "add_org_member",
            add_org_member_service_flow,
            sb=supabase,
            org_uri=org_uri,
            body=body,
        )

    async def add_org_project(self, *, org_uri: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "add_org_project",
            add_org_project_service_flow,
            sb=supabase,
            org_uri=org_uri,
            body=body,
        )

    async def add_executor_certificate(self, *, executor_id: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "add_executor_certificate",
            add_executor_certificate_service_flow,
            sb=supabase,
            executor_id=executor_id,
            body=body,
        )

    async def add_executor_skill(self, *, executor_id: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "add_executor_skill",
            add_executor_skill_service_flow,
            sb=supabase,
            executor_id=executor_id,
            body=body,
        )

    async def add_executor_requires(self, *, executor_id: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "add_executor_requires",
            add_executor_requires_service_flow,
            sb=supabase,
            executor_id=executor_id,
            body=body,
        )

    async def use_executor(self, *, executor_id: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "use_executor",
            use_executor_service_flow,
            sb=supabase,
            executor_id=executor_id,
            body=body,
        )

    async def maintain_executor(self, *, executor_id: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "maintain_executor",
            maintain_executor_service_flow,
            sb=supabase,
            executor_id=executor_id,
            body=body,
        )

    async def check_executor_certificate_expiry(self) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "check_executor_certificate_expiry",
            check_executor_certificate_expiry_service_flow,
            sb=supabase,
        )

    async def register_tool(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("register_tool", register_tool_service_flow, sb=supabase, body=body)

    async def get_tool(self, *, tool_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_tool", get_tool_service_flow, sb=supabase, tool_id=tool_id)

    async def get_tool_status(self, *, tool_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_tool_status", get_tool_status_service_flow, sb=supabase, tool_id=tool_id)

    async def list_tools(self, *, project_uri: str = "", owner_uri: str = "", tool_type: str = "", status: str = "") -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "list_tools",
            list_tools_service_flow,
            sb=supabase,
            project_uri=project_uri,
            owner_uri=owner_uri,
            tool_type=tool_type,
            status=status,
        )

    async def use_tool(self, *, tool_id: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("use_tool", use_tool_service_flow, sb=supabase, tool_id=tool_id, body=body)

    async def maintain_tool(self, *, tool_id: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("maintain_tool", maintain_tool_service_flow, sb=supabase, tool_id=tool_id, body=body)

    async def retire_tool(self, *, tool_id: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("retire_tool", retire_tool_service_flow, sb=supabase, tool_id=tool_id, body=body)

    async def check_tool_status(self) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("check_tool_status", check_tool_status_service_flow, sb=supabase)

    async def update_executor_holder(self, *, executor_uri: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "update_executor_holder",
            update_executor_holder_service_flow,
            sb=supabase,
            executor_uri=executor_uri,
            body=body,
        )

    async def sign(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("signpeg_sign", sign_service_flow, sb=supabase, body=body)

    async def verify(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("signpeg_verify", verify_service_flow, sb=supabase, body=body)

    async def status(self, *, doc_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("signpeg_status", status_service_flow, sb=supabase, doc_id=doc_id)

    async def delegate(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("signpeg_delegate", delegate_service_flow, sb=supabase, body=body)

    async def submit_acceptance(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("acceptance_submit", submit_acceptance_service_flow, sb=supabase, body=body)

    async def get_acceptance(self, *, acceptance_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "acceptance_get",
            get_acceptance_service_flow,
            sb=supabase,
            acceptance_id=acceptance_id,
        )

    async def sign_acceptance_condition(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "acceptance_condition_sign",
            sign_acceptance_condition_service_flow,
            sb=supabase,
            body=body,
        )

    async def explain_gate(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "signpeg_explain_gate",
            explain_gate_service_flow,
            sb=supabase,
            body=body,
        )

    async def explain_process(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "signpeg_explain_process",
            explain_process_service_flow,
            sb=supabase,
            body=body,
        )

    async def validate_field(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "signpeg_validate_field",
            validate_field_service_flow,
            sb=supabase,
            body=body,
        )

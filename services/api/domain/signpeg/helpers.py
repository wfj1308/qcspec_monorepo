"""SignPeg service helper wrappers."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.domain.signpeg.flows import (
    add_executor_requires_flow,
    add_org_member_flow,
    create_org_member_flow,
    update_org_member_flow,
    disable_org_member_flow,
    add_org_project_flow,
    check_tool_status_flow,
    add_executor_certificate_flow,
    add_executor_skill_flow,
    check_executor_certificate_expiry_flow,
    delegate_flow,
    explain_gate_flow,
    explain_process_flow,
    validate_field_flow,
    get_acceptance_flow,
    get_executor_by_id_flow,
    get_org_branches_flow,
    get_org_members_flow,
    get_executor_status_flow,
    import_executors_flow,
    list_executors_flow,
    get_executor_flow,
    register_executorpeg_flow,
    register_executor_flow,
    register_tool_flow,
    search_executors_flow,
    get_tool_flow,
    get_tool_status_flow,
    list_tools_flow,
    use_tool_flow,
    maintain_tool_flow,
    maintain_executor_flow,
    retire_tool_flow,
    sign_acceptance_condition_flow,
    sign_flow,
    status_flow,
    submit_acceptance_flow,
    use_executor_flow,
    update_executor_holder_flow,
    verify_flow,
)


def register_executor_service_flow(*, sb: Client, body: Any) -> dict[str, Any]:
    return register_executor_flow(sb=sb, body=body)


def register_executorpeg_service_flow(*, sb: Client, body: Any) -> dict[str, Any]:
    return register_executorpeg_flow(sb=sb, body=body)


def import_executors_service_flow(*, sb: Client, body: Any) -> dict[str, Any]:
    return import_executors_flow(sb=sb, body=body)


def get_executor_service_flow(*, sb: Client, executor_uri: str) -> dict[str, Any]:
    return get_executor_flow(sb=sb, executor_uri=executor_uri)


def get_executor_by_id_service_flow(*, sb: Client, executor_id: str) -> dict[str, Any]:
    return get_executor_by_id_flow(sb=sb, executor_id=executor_id)


def get_executor_status_service_flow(*, sb: Client, executor_id: str) -> dict[str, Any]:
    return get_executor_status_flow(sb=sb, executor_id=executor_id)


def list_executors_service_flow(*, sb: Client, org_uri: str = "") -> dict[str, Any]:
    return list_executors_flow(sb=sb, org_uri=org_uri)


def search_executors_service_flow(*, sb: Client, body: Any) -> dict[str, Any]:
    return search_executors_flow(sb=sb, query=body)


def get_org_members_service_flow(*, sb: Client, org_uri: str) -> dict[str, Any]:
    return get_org_members_flow(sb=sb, org_uri=org_uri)


def get_org_branches_service_flow(*, sb: Client, org_uri: str) -> dict[str, Any]:
    return get_org_branches_flow(sb=sb, org_uri=org_uri)


def add_org_member_service_flow(*, sb: Client, org_uri: str, body: Any) -> dict[str, Any]:
    return add_org_member_flow(sb=sb, org_uri=org_uri, body=body)


def create_org_member_service_flow(*, sb: Client, org_uri: str, body: Any) -> dict[str, Any]:
    return create_org_member_flow(sb=sb, org_uri=org_uri, body=body)


def update_org_member_service_flow(*, sb: Client, org_uri: str, member_executor_uri: str, body: Any) -> dict[str, Any]:
    return update_org_member_flow(sb=sb, org_uri=org_uri, member_executor_uri=member_executor_uri, body=body)


def disable_org_member_service_flow(*, sb: Client, org_uri: str, member_executor_uri: str, body: Any) -> dict[str, Any]:
    return disable_org_member_flow(sb=sb, org_uri=org_uri, member_executor_uri=member_executor_uri, body=body)


def add_org_project_service_flow(*, sb: Client, org_uri: str, body: Any) -> dict[str, Any]:
    return add_org_project_flow(sb=sb, org_uri=org_uri, body=body)


def add_executor_certificate_service_flow(*, sb: Client, executor_id: str, body: Any) -> dict[str, Any]:
    return add_executor_certificate_flow(sb=sb, executor_id=executor_id, body=body)


def add_executor_skill_service_flow(*, sb: Client, executor_id: str, body: Any) -> dict[str, Any]:
    return add_executor_skill_flow(sb=sb, executor_id=executor_id, body=body)


def add_executor_requires_service_flow(*, sb: Client, executor_id: str, body: Any) -> dict[str, Any]:
    return add_executor_requires_flow(sb=sb, executor_id=executor_id, body=body)


def use_executor_service_flow(*, sb: Client, executor_id: str, body: Any) -> dict[str, Any]:
    return use_executor_flow(sb=sb, executor_id=executor_id, body=body)


def maintain_executor_service_flow(*, sb: Client, executor_id: str, body: Any) -> dict[str, Any]:
    return maintain_executor_flow(sb=sb, executor_id=executor_id, body=body)


def check_executor_certificate_expiry_service_flow(*, sb: Client) -> dict[str, Any]:
    return check_executor_certificate_expiry_flow(sb=sb)


def register_tool_service_flow(*, sb: Client, body: Any) -> dict[str, Any]:
    return register_tool_flow(sb=sb, body=body)


def get_tool_service_flow(*, sb: Client, tool_id: str) -> dict[str, Any]:
    return get_tool_flow(sb=sb, tool_id=tool_id)


def get_tool_status_service_flow(*, sb: Client, tool_id: str) -> dict[str, Any]:
    return get_tool_status_flow(sb=sb, tool_id=tool_id)


def list_tools_service_flow(*, sb: Client, project_uri: str = "", owner_uri: str = "", tool_type: str = "", status: str = "") -> dict[str, Any]:
    return list_tools_flow(sb=sb, project_uri=project_uri, owner_uri=owner_uri, tool_type=tool_type, status=status)


def use_tool_service_flow(*, sb: Client, tool_id: str, body: Any) -> dict[str, Any]:
    return use_tool_flow(sb=sb, tool_id=tool_id, body=body)


def maintain_tool_service_flow(*, sb: Client, tool_id: str, body: Any) -> dict[str, Any]:
    return maintain_tool_flow(sb=sb, tool_id=tool_id, body=body)


def retire_tool_service_flow(*, sb: Client, tool_id: str, body: Any) -> dict[str, Any]:
    return retire_tool_flow(sb=sb, tool_id=tool_id, body=body)


def check_tool_status_service_flow(*, sb: Client) -> dict[str, Any]:
    return check_tool_status_flow(sb=sb)


def update_executor_holder_service_flow(*, sb: Client, executor_uri: str, body: Any) -> dict[str, Any]:
    return update_executor_holder_flow(sb=sb, executor_uri=executor_uri, body=body)


def sign_service_flow(*, sb: Client, body: Any) -> dict[str, Any]:
    return sign_flow(sb=sb, body=body)


def verify_service_flow(*, sb: Client, body: Any) -> dict[str, Any]:
    return verify_flow(sb=sb, body=body)


def status_service_flow(*, sb: Client, doc_id: str) -> dict[str, Any]:
    return status_flow(sb=sb, doc_id=doc_id)


async def delegate_service_flow(*, sb: Client, body: Any) -> dict[str, Any]:
    return await delegate_flow(sb=sb, body=body)


def submit_acceptance_service_flow(*, sb: Client, body: Any) -> dict[str, Any]:
    return submit_acceptance_flow(sb=sb, body=body)


def get_acceptance_service_flow(*, sb: Client, acceptance_id: str) -> dict[str, Any]:
    return get_acceptance_flow(sb=sb, acceptance_id=acceptance_id)


def sign_acceptance_condition_service_flow(*, sb: Client, body: Any) -> dict[str, Any]:
    return sign_acceptance_condition_flow(sb=sb, body=body)


async def explain_gate_service_flow(*, sb: Client, body: Any) -> dict[str, Any]:
    return await explain_gate_flow(sb=sb, body=body)


def explain_process_service_flow(*, sb: Client, body: Any) -> dict[str, Any]:
    return explain_process_flow(sb=sb, body=body)


async def validate_field_service_flow(*, sb: Client, body: Any) -> dict[str, Any]:
    return await validate_field_flow(sb=sb, body=body)

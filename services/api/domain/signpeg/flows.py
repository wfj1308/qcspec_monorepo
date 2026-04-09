"""SignPeg flow entrypoints."""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote

from services.api.domain.signpeg.models import (
    AcceptanceConditionSignRequest,
    AcceptanceSubmitRequest,
    CertificateAddRequest,
    DelegationRequest,
    ExecutorCreateRequest,
    ExecutorImportRequest,
    ExecutorMaintainRequest,
    ExecutorRegisterRequest,
    ExecutorSearchRequest,
    ExecutorUseRequest,
    FieldValidateRequest,
    GateExplainRequest,
    HolderChangeRequest,
    OrgMemberAddRequest,
    OrgProjectAddRequest,
    ProcessExplainRequest,
    RequiresAddRequest,
    SignPegRequest,
    SkillAddRequest,
    ToolMaintainRequest,
    ToolRegisterRequest,
    ToolRetireRequest,
    ToolUseRequest,
    VerifyRequest,
)
from services.api.domain.signpeg.runtime import (
    ExecutorScheduler,
    add_executor_certificate,
    add_executor_requires,
    add_executor_skill,
    check_executor_certificate_expiry,
    explain_gate,
    explain_process,
    validate_field,
    get_acceptance,
    get_executor_record_by_id,
    get_executor_status,
    get_org_members,
    get_org_branches,
    add_org_member,
    add_org_project,
    list_executors,
    get_executor_record,
    register_executorpeg,
    register_executor,
    maintain_executor,
    search_executors,
    register_tool,
    get_tool,
    get_tool_status,
    list_tools,
    use_tool,
    maintain_tool,
    retire_tool,
    check_tool_status,
    sign_acceptance_condition,
    sign,
    status,
    submit_acceptance,
    use_executor,
    update_executor_holder,
    verify,
)
from services.api.domain.signpeg.runtime.signpeg import _get_executor


def _decode_executor_uri(value: str) -> str:
    return unquote(str(value or "").strip())


def register_executor_flow(*, sb: Any, body: ExecutorRegisterRequest) -> dict[str, Any]:
    executor = register_executor(sb=sb, body=body)
    return {"ok": True, "executor": executor.model_dump(mode="json")}


def register_executorpeg_flow(*, sb: Any, body: ExecutorCreateRequest) -> dict[str, Any]:
    payload = body if isinstance(body, ExecutorCreateRequest) else ExecutorCreateRequest.model_validate(body)
    executor = register_executorpeg(sb=sb, body=payload)
    return {
        "ok": True,
        "executor_uri": executor.executor_uri,
        "executor_id": executor.executor_id,
        "registration_proof": executor.registration_proof,
        "status": executor.status,
        "executor": executor.model_dump(mode="json"),
    }


def import_executors_flow(*, sb: Any, body: ExecutorImportRequest) -> dict[str, Any]:
    payload = body if isinstance(body, ExecutorImportRequest) else ExecutorImportRequest.model_validate(body)
    imported: list[dict[str, Any]] = []
    for item in payload.items:
        executor = register_executorpeg(sb=sb, body=item)
        imported.append(
            {
                "executor_id": executor.executor_id,
                "executor_uri": executor.executor_uri,
                "name": executor.name,
                "status": executor.status,
            }
        )
    return {"ok": True, "count": len(imported), "items": imported}


def get_executor_flow(*, sb: Any, executor_uri: str) -> dict[str, Any]:
    record = get_executor_record(sb=sb, executor_uri=_decode_executor_uri(executor_uri))
    return {"ok": True, **record.model_dump(mode="json")}


def get_executor_by_id_flow(*, sb: Any, executor_id: str) -> dict[str, Any]:
    record = get_executor_record_by_id(sb=sb, executor_id=_decode_executor_uri(executor_id))
    return {"ok": True, **record.model_dump(mode="json")}


def get_executor_status_flow(*, sb: Any, executor_id: str) -> dict[str, Any]:
    out = get_executor_status(sb=sb, executor_id=_decode_executor_uri(executor_id))
    return {"ok": True, **out.model_dump(mode="json")}


def list_executors_flow(*, sb: Any, org_uri: str = "") -> dict[str, Any]:
    out = list_executors(sb=sb, org_uri=_decode_executor_uri(org_uri))
    return {"ok": True, **out.model_dump(mode="json")}


def search_executors_flow(*, sb: Any, query: ExecutorSearchRequest) -> dict[str, Any]:
    payload = query if isinstance(query, ExecutorSearchRequest) else ExecutorSearchRequest.model_validate(query)
    out = search_executors(sb=sb, query=payload)
    return {"ok": True, **out.model_dump(mode="json")}


def get_org_members_flow(*, sb: Any, org_uri: str) -> dict[str, Any]:
    return {"ok": True, **get_org_members(sb=sb, org_uri=_decode_executor_uri(org_uri))}


def get_org_branches_flow(*, sb: Any, org_uri: str) -> dict[str, Any]:
    return {"ok": True, **get_org_branches(sb=sb, org_uri=_decode_executor_uri(org_uri))}


def add_org_member_flow(*, sb: Any, org_uri: str, body: OrgMemberAddRequest) -> dict[str, Any]:
    payload = body if isinstance(body, OrgMemberAddRequest) else OrgMemberAddRequest.model_validate(body)
    return add_org_member(sb=sb, org_uri=_decode_executor_uri(org_uri), body=payload)


def add_org_project_flow(*, sb: Any, org_uri: str, body: OrgProjectAddRequest) -> dict[str, Any]:
    payload = body if isinstance(body, OrgProjectAddRequest) else OrgProjectAddRequest.model_validate(body)
    return add_org_project(sb=sb, org_uri=_decode_executor_uri(org_uri), body=payload)


def add_executor_certificate_flow(*, sb: Any, executor_id: str, body: CertificateAddRequest) -> dict[str, Any]:
    payload = body if isinstance(body, CertificateAddRequest) else CertificateAddRequest.model_validate(body)
    out = add_executor_certificate(sb=sb, executor_id=_decode_executor_uri(executor_id), body=payload)
    return {"ok": True, "executor": out.model_dump(mode="json")}


def add_executor_skill_flow(*, sb: Any, executor_id: str, body: SkillAddRequest) -> dict[str, Any]:
    payload = body if isinstance(body, SkillAddRequest) else SkillAddRequest.model_validate(body)
    out = add_executor_skill(sb=sb, executor_id=_decode_executor_uri(executor_id), body=payload)
    return {"ok": True, "executor": out.model_dump(mode="json")}


def add_executor_requires_flow(*, sb: Any, executor_id: str, body: RequiresAddRequest) -> dict[str, Any]:
    payload = body if isinstance(body, RequiresAddRequest) else RequiresAddRequest.model_validate(body)
    out = add_executor_requires(sb=sb, executor_id=_decode_executor_uri(executor_id), body=payload)
    return {"ok": True, "executor": out.model_dump(mode="json")}


def use_executor_flow(*, sb: Any, executor_id: str, body: ExecutorUseRequest) -> dict[str, Any]:
    payload = body if isinstance(body, ExecutorUseRequest) else ExecutorUseRequest.model_validate(body)
    return use_executor(sb=sb, executor_id=_decode_executor_uri(executor_id), body=payload)


def maintain_executor_flow(*, sb: Any, executor_id: str, body: ExecutorMaintainRequest) -> dict[str, Any]:
    payload = body if isinstance(body, ExecutorMaintainRequest) else ExecutorMaintainRequest.model_validate(body)
    return maintain_executor(sb=sb, executor_id=_decode_executor_uri(executor_id), body=payload)


def check_executor_certificate_expiry_flow(*, sb: Any) -> dict[str, Any]:
    return check_executor_certificate_expiry(sb=sb)


def register_tool_flow(*, sb: Any, body: ToolRegisterRequest) -> dict[str, Any]:
    payload = body if isinstance(body, ToolRegisterRequest) else ToolRegisterRequest.model_validate(body)
    tool = register_tool(sb=sb, body=payload)
    return {
        "ok": True,
        "tool_id": tool.tool_id,
        "tool_uri": tool.tool_uri,
        "registration_proof": tool.registration_proof,
        "status": tool.status,
        "tool": tool.model_dump(mode="json"),
    }


def get_tool_flow(*, sb: Any, tool_id: str) -> dict[str, Any]:
    out = get_tool(sb=sb, tool_id=_decode_executor_uri(tool_id))
    return {"ok": True, "tool": out.model_dump(mode="json")}


def get_tool_status_flow(*, sb: Any, tool_id: str) -> dict[str, Any]:
    out = get_tool_status(sb=sb, tool_id=_decode_executor_uri(tool_id))
    return {"ok": True, **out.model_dump(mode="json")}


def list_tools_flow(*, sb: Any, project_uri: str = "", owner_uri: str = "", tool_type: str = "", status: str = "") -> dict[str, Any]:
    out = list_tools(
        sb=sb,
        project_uri=_decode_executor_uri(project_uri),
        owner_uri=_decode_executor_uri(owner_uri),
        tool_type=tool_type,
        status=status,
    )
    return {"ok": True, **out.model_dump(mode="json")}


def use_tool_flow(*, sb: Any, tool_id: str, body: ToolUseRequest) -> dict[str, Any]:
    payload = body if isinstance(body, ToolUseRequest) else ToolUseRequest.model_validate(body)
    out = use_tool(sb=sb, tool_id=_decode_executor_uri(tool_id), body=payload)
    return {"ok": True, **out.model_dump(mode="json")}


def maintain_tool_flow(*, sb: Any, tool_id: str, body: ToolMaintainRequest) -> dict[str, Any]:
    payload = body if isinstance(body, ToolMaintainRequest) else ToolMaintainRequest.model_validate(body)
    return maintain_tool(sb=sb, tool_id=_decode_executor_uri(tool_id), body=payload)


def retire_tool_flow(*, sb: Any, tool_id: str, body: ToolRetireRequest) -> dict[str, Any]:
    payload = body if isinstance(body, ToolRetireRequest) else ToolRetireRequest.model_validate(body)
    return retire_tool(sb=sb, tool_id=_decode_executor_uri(tool_id), body=payload)


def check_tool_status_flow(*, sb: Any) -> dict[str, Any]:
    return check_tool_status(sb=sb)


def update_executor_holder_flow(*, sb: Any, executor_uri: str, body: HolderChangeRequest) -> dict[str, Any]:
    executor = update_executor_holder(sb=sb, executor_uri=_decode_executor_uri(executor_uri), body=body)
    return {"ok": True, "executor": executor.model_dump(mode="json")}


def sign_flow(*, sb: Any, body: SignPegRequest) -> dict[str, Any]:
    executor = _get_executor(sb, body.executor_uri)
    out = sign(sb=sb, req=body, executor=executor)
    return {"ok": True, **out.model_dump(mode="json")}


def verify_flow(*, sb: Any, body: VerifyRequest) -> dict[str, Any]:
    out = verify(sb=sb, body=body)
    return {"ok": True, **out.model_dump(mode="json")}


def status_flow(*, sb: Any, doc_id: str) -> dict[str, Any]:
    out = status(sb=sb, doc_id=doc_id)
    return {"ok": True, **out.model_dump(mode="json")}


async def delegate_flow(*, sb: Any, body: DelegationRequest) -> dict[str, Any]:
    scheduler = ExecutorScheduler(sb=sb)
    out = await scheduler.delegate(body)
    return {"ok": True, "delegation": out.model_dump(mode="json")}


def submit_acceptance_flow(*, sb: Any, body: AcceptanceSubmitRequest) -> dict[str, Any]:
    out = submit_acceptance(sb=sb, body=body)
    return {"ok": True, **out.model_dump(mode="json")}


def get_acceptance_flow(*, sb: Any, acceptance_id: str) -> dict[str, Any]:
    out = get_acceptance(sb=sb, acceptance_id=str(acceptance_id or "").strip())
    return {"ok": True, "acceptance": out.model_dump(mode="json")}


def sign_acceptance_condition_flow(*, sb: Any, body: AcceptanceConditionSignRequest) -> dict[str, Any]:
    out = sign_acceptance_condition(sb=sb, body=body)
    return {"ok": True, **out.model_dump(mode="json")}


async def explain_gate_flow(*, sb: Any, body: GateExplainRequest) -> dict[str, Any]:
    out = await explain_gate(body=body)
    return {"ok": True, "result": out.model_dump(mode="json")}


def explain_process_flow(*, sb: Any, body: ProcessExplainRequest) -> dict[str, Any]:
    out = explain_process(sb=sb, body=body)
    return {"ok": True, "result": out.model_dump(mode="json")}


async def validate_field_flow(*, sb: Any, body: FieldValidateRequest) -> dict[str, Any]:
    out = await validate_field(body=body)
    return {"ok": True, "result": out.model_dump(mode="json")}

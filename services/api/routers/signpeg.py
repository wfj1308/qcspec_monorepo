"""SignPeg routes: executor registry and signature lifecycle."""

from __future__ import annotations

from urllib.parse import unquote

from fastapi import APIRouter, Depends, Query

from services.api.dependencies import get_signpeg_service
from services.api.domain import SignPegService
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

router = APIRouter()


def _decode_uri(raw: str) -> str:
    return unquote(str(raw or "").strip())


@router.post("/api/v1/signpeg/sign")
async def signpeg_sign(
    body: SignPegRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.sign(body=body)


@router.post("/api/v1/signpeg/verify")
async def signpeg_verify(
    body: VerifyRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.verify(body=body)


@router.get("/api/v1/signpeg/status/{doc_id}")
async def signpeg_status(
    doc_id: str,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.status(doc_id=doc_id)


@router.post("/api/v1/executor/register")
async def executor_register(
    body: ExecutorRegisterRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.register_executor(body=body)


@router.post("/api/v1/executors/register")
async def executors_register(
    body: ExecutorCreateRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.register_executorpeg(body=body)


@router.post("/api/v1/executors/import")
async def executors_import(
    body: ExecutorImportRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.import_executors(body=body)


@router.put("/api/v1/executor/{executor_uri:path}/holder")
async def executor_update_holder(
    executor_uri: str,
    body: HolderChangeRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.update_executor_holder(executor_uri=_decode_uri(executor_uri), body=body)


@router.get("/api/v1/executor/{executor_uri:path}")
async def executor_get(
    executor_uri: str,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.get_executor(executor_uri=_decode_uri(executor_uri))


@router.get("/api/v1/executors/list")
async def executors_list(
    org_uri: str = Query(""),
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.list_executors(org_uri=org_uri)


@router.get("/api/v1/executors/search")
async def executors_search(
    skill_uri: str = Query(""),
    org_uri: str = Query(""),
    type: str = Query(""),  # noqa: A002
    available: bool = Query(False),
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.search_executors(
        body=ExecutorSearchRequest(skill_uri=skill_uri, org_uri=org_uri, type=type, available=bool(available))
    )


@router.get("/api/v1/executors/orgs/{org_uri:path}/members")
async def org_members(
    org_uri: str,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.get_org_members(org_uri=_decode_uri(org_uri))


@router.get("/api/v1/executors/orgs/{org_uri:path}/branches")
async def org_branches(
    org_uri: str,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.get_org_branches(org_uri=_decode_uri(org_uri))


@router.post("/api/v1/executors/orgs/{org_uri:path}/members/add")
async def org_add_member(
    org_uri: str,
    body: OrgMemberAddRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.add_org_member(org_uri=_decode_uri(org_uri), body=body)


@router.post("/api/v1/executors/orgs/{org_uri:path}/projects/add")
async def org_add_project(
    org_uri: str,
    body: OrgProjectAddRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.add_org_project(org_uri=_decode_uri(org_uri), body=body)


@router.get("/api/v1/executors/{executor_id}/status")
async def executors_get_status(
    executor_id: str,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.get_executor_status(executor_id=executor_id)


@router.get("/api/v1/executors/{executor_id}")
async def executors_get_by_id(
    executor_id: str,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.get_executor_by_id(executor_id=executor_id)


@router.post("/api/v1/executors/{executor_id}/certificates/add")
async def executors_add_certificate(
    executor_id: str,
    body: CertificateAddRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.add_executor_certificate(executor_id=executor_id, body=body)


@router.post("/api/v1/executors/{executor_id}/skills/add")
async def executors_add_skill(
    executor_id: str,
    body: SkillAddRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.add_executor_skill(executor_id=executor_id, body=body)


@router.post("/api/v1/executors/{executor_id}/requires/add")
async def executors_add_requires(
    executor_id: str,
    body: RequiresAddRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.add_executor_requires(executor_id=executor_id, body=body)


@router.post("/api/v1/executors/{executor_id}/use")
async def executors_use(
    executor_id: str,
    body: ExecutorUseRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.use_executor(executor_id=executor_id, body=body)


@router.post("/api/v1/executors/{executor_id}/maintain")
async def executors_maintain(
    executor_id: str,
    body: ExecutorMaintainRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.maintain_executor(executor_id=executor_id, body=body)


@router.get("/api/v1/tools/list")
async def tools_list(
    project_uri: str = Query(""),
    owner_uri: str = Query(""),
    tool_type: str = Query(""),
    status: str = Query(""),
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.list_tools(
        project_uri=project_uri,
        owner_uri=owner_uri,
        tool_type=tool_type,
        status=status,
    )


@router.post("/api/v1/tools/register")
async def tools_register(
    body: ToolRegisterRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.register_tool(body=body)


@router.get("/api/v1/tools/{tool_id}/status")
async def tools_status(
    tool_id: str,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.get_tool_status(tool_id=tool_id)


@router.get("/api/v1/tools/{tool_id}")
async def tools_get(
    tool_id: str,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.get_tool(tool_id=tool_id)


@router.post("/api/v1/tools/{tool_id}/use")
async def tools_use(
    tool_id: str,
    body: ToolUseRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.use_tool(tool_id=tool_id, body=body)


@router.post("/api/v1/tools/{tool_id}/maintain")
async def tools_maintain(
    tool_id: str,
    body: ToolMaintainRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.maintain_tool(tool_id=tool_id, body=body)


@router.post("/api/v1/tools/{tool_id}/retire")
async def tools_retire(
    tool_id: str,
    body: ToolRetireRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.retire_tool(tool_id=tool_id, body=body)


@router.post("/api/v1/executor/delegate")
async def executor_delegate(
    body: DelegationRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.delegate(body=body)


@router.post("/api/v1/acceptance/submit")
async def acceptance_submit(
    body: AcceptanceSubmitRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.submit_acceptance(body=body)


@router.get("/api/v1/acceptance/{acceptance_id}")
async def acceptance_get(
    acceptance_id: str,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.get_acceptance(acceptance_id=acceptance_id)


@router.post("/api/v1/acceptance/condition/sign")
async def acceptance_condition_sign(
    body: AcceptanceConditionSignRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.sign_acceptance_condition(body=body)


@router.post("/api/v1/explain/gate")
async def explain_gate(
    body: GateExplainRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.explain_gate(body=body)


@router.post("/api/v1/explain/process")
async def explain_process(
    body: ProcessExplainRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.explain_process(body=body)


@router.post("/api/v1/explain/field-validate")
async def validate_field_realtime(
    body: FieldValidateRequest,
    signpeg_service: SignPegService = Depends(get_signpeg_service),
):
    return await signpeg_service.validate_field(body=body)

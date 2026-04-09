"""Process-chain material IQC API routes."""

from __future__ import annotations

from urllib.parse import unquote

from fastapi import APIRouter, Depends, Query

from services.api.core.docpeg import DocPegExecutionGateService
from services.api.dependencies import (
    get_boqpeg_service,
    get_docpeg_execution_gate_service,
    require_auth_identity,
)
from services.api.domain import BOQPegService
from services.api.domain.boqpeg.models import (
    EquipmentTripRequest,
    FormworkUseTripRequest,
    IQCSubmitRequest,
    InspectionBatchCreateRequest,
    PrestressingTripRequest,
    ToolAssetRegisterRequest,
    WeldingTripRequest,
)

router = APIRouter()


def _decode_uri(raw: str) -> str:
    return unquote(str(raw or "").strip()).rstrip("/")


@router.get("/api/v1/process/{component_uri:path}/materials")
async def get_process_materials(
    component_uri: str,
    project_uri: str = Query(...),
    identity: dict = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    decoded_component_uri = _decode_uri(component_uri)
    docpeg_gate.enforce_execution(
        identity=identity,
        operation="boqpeg_get_process_materials",
        access_mode="read",
        project_uri=project_uri,
        node_uri=f"{decoded_component_uri}/process-chain/main",
    )
    return await boqpeg_service.get_process_materials(
        project_uri=project_uri,
        component_uri=decoded_component_uri,
    )


@router.post("/api/v1/iqc/submit")
async def submit_iqc(
    body: IQCSubmitRequest,
    commit: bool = Query(True),
    identity: dict = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    payload = body.model_dump(mode="json")
    docpeg_gate.enforce_execution(
        identity=identity,
        operation="boqpeg_submit_iqc",
        access_mode="write",
        project_uri=str(payload.get("project_uri") or ""),
        node_uri=f"{str(payload.get('component_uri') or '').rstrip('/')}/iqc",
        actor_uri=str(payload.get("executor_uri") or ""),
    )
    return await boqpeg_service.submit_iqc(body=payload, commit=bool(commit))


@router.post("/api/v1/inspection-batch/create")
async def create_inspection_batch(
    body: InspectionBatchCreateRequest,
    commit: bool = Query(True),
    identity: dict = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    payload = body.model_dump(mode="json")
    docpeg_gate.enforce_execution(
        identity=identity,
        operation="boqpeg_create_inspection_batch",
        access_mode="write",
        project_uri=str(payload.get("project_uri") or ""),
        node_uri=f"{str(payload.get('component_uri') or '').rstrip('/')}/inspection-batch",
        actor_uri=str(payload.get("executor_uri") or ""),
    )
    return await boqpeg_service.create_inspection_batch(body=payload, commit=bool(commit))


@router.get("/api/v1/material-utxo/component/{component_uri:path}")
async def get_material_utxo_by_component(
    component_uri: str,
    identity: dict = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    decoded = _decode_uri(component_uri)
    docpeg_gate.enforce_execution(
        identity=identity,
        operation="boqpeg_get_material_utxo_by_component",
        access_mode="read",
        project_uri="",
        node_uri=decoded,
    )
    return await boqpeg_service.get_material_utxo_by_component(component_uri=decoded)


@router.get("/api/v1/material-utxo/{iqc_uri:path}")
async def get_material_utxo_by_iqc(
    iqc_uri: str,
    identity: dict = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    decoded = _decode_uri(iqc_uri)
    docpeg_gate.enforce_execution(
        identity=identity,
        operation="boqpeg_get_material_utxo_by_iqc",
        access_mode="read",
        project_uri="",
        node_uri=decoded,
    )
    return await boqpeg_service.get_material_utxo_by_iqc(iqc_uri=decoded)


@router.post("/api/v1/trip/welding")
async def submit_welding_trip(
    body: WeldingTripRequest,
    commit: bool = Query(True),
    identity: dict = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    payload = body.model_dump(mode="json", by_alias=True)
    docpeg_gate.enforce_execution(
        identity=identity,
        operation="boqpeg_submit_welding_trip",
        access_mode="write",
        project_uri=str(payload.get("project_uri") or ""),
        node_uri=f"{str(payload.get('component_uri') or '').rstrip('/')}/trip/welding",
        actor_uri=str(payload.get("executor_uri") or ""),
    )
    return await boqpeg_service.submit_welding_trip(body=payload, commit=bool(commit))


@router.post("/api/v1/trip/formwork-use")
async def submit_formwork_use_trip(
    body: FormworkUseTripRequest,
    commit: bool = Query(True),
    identity: dict = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    payload = body.model_dump(mode="json", by_alias=True)
    docpeg_gate.enforce_execution(
        identity=identity,
        operation="boqpeg_submit_formwork_use_trip",
        access_mode="write",
        project_uri=str(payload.get("project_uri") or ""),
        node_uri=f"{str(payload.get('component_uri') or '').rstrip('/')}/trip/formwork",
        actor_uri=str(payload.get("executor_uri") or ""),
    )
    return await boqpeg_service.submit_formwork_use_trip(body=payload, commit=bool(commit))


@router.post("/api/v1/trip/prestressing")
async def submit_prestressing_trip(
    body: PrestressingTripRequest,
    commit: bool = Query(True),
    identity: dict = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    payload = body.model_dump(mode="json", by_alias=True)
    docpeg_gate.enforce_execution(
        identity=identity,
        operation="boqpeg_submit_prestressing_trip",
        access_mode="write",
        project_uri=str(payload.get("project_uri") or ""),
        node_uri=f"{str(payload.get('component_uri') or '').rstrip('/')}/trip/prestressing",
        actor_uri=str(payload.get("executor_uri") or ""),
    )
    return await boqpeg_service.submit_prestressing_trip(body=payload, commit=bool(commit))


@router.post("/api/v1/equipment/register")
async def register_tool_asset(
    body: ToolAssetRegisterRequest,
    commit: bool = Query(True),
    identity: dict = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    payload = body.model_dump(mode="json", by_alias=True)
    project_uri = str(payload.get("project_uri") or "")
    equipment_uri = str(payload.get("v_uri") or "").rstrip("/")
    docpeg_gate.enforce_execution(
        identity=identity,
        operation="boqpeg_register_tool_asset",
        access_mode="write",
        project_uri=project_uri,
        node_uri=f"{equipment_uri}/asset-register",
        actor_uri=str(payload.get("executor_uri") or ""),
    )
    return await boqpeg_service.register_tool_asset(body=payload, commit=bool(commit))


@router.post("/api/v1/equipment/trip")
async def submit_equipment_trip(
    body: EquipmentTripRequest,
    commit: bool = Query(True),
    identity: dict = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    payload = body.model_dump(mode="json", by_alias=True)
    docpeg_gate.enforce_execution(
        identity=identity,
        operation="boqpeg_submit_equipment_trip",
        access_mode="write",
        project_uri=str(payload.get("project_uri") or ""),
        node_uri=f"{str(payload.get('component_uri') or '').rstrip('/')}/trip/equipment",
        actor_uri=str(payload.get("operator_executor_uri") or ""),
    )
    return await boqpeg_service.submit_equipment_trip(body=payload, commit=bool(commit))


@router.get("/api/v1/equipment/{equipment_uri:path}/status")
async def get_equipment_status(
    equipment_uri: str,
    operator_executor_uri: str = Query(""),
    identity: dict = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    decoded = _decode_uri(equipment_uri)
    docpeg_gate.enforce_execution(
        identity=identity,
        operation="boqpeg_get_equipment_status",
        access_mode="read",
        project_uri="",
        node_uri=f"{decoded}/status",
        actor_uri=operator_executor_uri,
    )
    return await boqpeg_service.get_equipment_status(
        equipment_uri=decoded,
        operator_executor_uri=str(operator_executor_uri or "").strip(),
    )


@router.get("/api/v1/equipment/{equipment_uri:path}/history")
async def get_equipment_history(
    equipment_uri: str,
    identity: dict = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    decoded = _decode_uri(equipment_uri)
    docpeg_gate.enforce_execution(
        identity=identity,
        operation="boqpeg_get_equipment_history",
        access_mode="read",
        project_uri="",
        node_uri=f"{decoded}/history",
    )
    return await boqpeg_service.get_equipment_history(equipment_uri=decoded)


@router.get("/api/v1/cost/component/{component_uri:path}")
async def get_component_cost(
    component_uri: str,
    overhead_ratio: float = Query(0.08),
    identity: dict = Depends(require_auth_identity),
    docpeg_gate: DocPegExecutionGateService = Depends(get_docpeg_execution_gate_service),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    decoded = _decode_uri(component_uri)
    docpeg_gate.enforce_execution(
        identity=identity,
        operation="boqpeg_calculate_component_cost",
        access_mode="read",
        project_uri="",
        node_uri=f"{decoded}/cost",
    )
    return await boqpeg_service.calculate_component_cost(component_uri=decoded, overhead_ratio=float(overhead_ratio))

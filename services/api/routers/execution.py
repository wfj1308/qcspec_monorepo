"""Execution routes for TripRole, remediation, and frequency workflows."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from services.api.dependencies import get_execution_service
from services.api.domain import ExecutionService
from services.api.domain.proof.schemas import (
    ComponentUTXOVerifyBody,
    FrequencyCalcBody,
    LabTestRecordBody,
    OfflineReplayBody,
    RemediationCloseBody,
    RemediationOpenBody,
    RemediationReinspectBody,
    ScanConfirmBody,
    SensorIngestBody,
    TransferAssetBody,
    TripRoleExecuteBody,
    VariationApplyBody,
)

router = APIRouter()


@router.post("/triprole/execute")
async def execute_triprole(
    body: TripRoleExecuteBody,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.execute_triprole(body=body)


@router.post("/triprole/hardware/ingest")
async def ingest_triprole_sensor_data(
    body: SensorIngestBody,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.ingest_sensor_data(body=body)


@router.post("/lab/record")
async def record_lab_test(
    body: LabTestRecordBody,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.record_lab_test(body=body)


@router.post("/frequency/calc")
async def calc_frequency(
    body: FrequencyCalcBody,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.calc_frequency(body=body)


@router.get("/frequency/dashboard")
async def frequency_dashboard(
    project_uri: str,
    limit_items: int = 200,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.get_frequency_dashboard(project_uri=project_uri, limit_items=limit_items)


@router.get("/triprole/provenance/{utxo_id}")
async def get_triprole_provenance(
    utxo_id: str,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.get_provenance(utxo_id=utxo_id)


@router.get("/triprole/aggregate-chain/{utxo_id}")
async def get_triprole_aggregate_chain(
    utxo_id: str,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.get_provenance(utxo_id=utxo_id)


@router.get("/triprole/full-lineage/{utxo_id}")
async def get_triprole_full_lineage(
    utxo_id: str,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.get_full_lineage(utxo_id=utxo_id)


@router.get("/triprole/asset-origin")
async def get_triprole_asset_origin(
    utxo_id: str = "",
    boq_item_uri: str = "",
    project_uri: str = "",
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.trace_asset_origin(
        utxo_id=utxo_id,
        boq_item_uri=boq_item_uri,
        project_uri=project_uri,
    )


@router.get("/identity/reputation")
async def get_identity_reputation(
    project_uri: str,
    participant_did: str,
    window_days: int = 90,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.did_reputation(
        project_uri=project_uri,
        participant_did=participant_did,
        window_days=window_days,
    )


@router.post("/triprole/transfer-asset")
async def transfer_triprole_asset(
    body: TransferAssetBody,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.transfer_asset(body=body)


@router.post("/triprole/component/verify")
async def verify_triprole_component_utxo(
    body: ComponentUTXOVerifyBody,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.verify_component_utxo(body=body)


@router.post("/triprole/apply-variation")
async def apply_triprole_variation(
    body: VariationApplyBody,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.apply_variation(body=body)


@router.post("/triprole/offline/replay")
async def replay_triprole_offline_packets(
    body: OfflineReplayBody,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.replay_offline_packets(body=body)


@router.post("/triprole/scan-confirm")
async def scan_confirm_triprole_signature(
    body: ScanConfirmBody,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.scan_confirm_signature(body=body)


@router.post("/remediation/open")
async def open_remediation(
    body: RemediationOpenBody,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.open_remediation(body=body)


@router.post("/remediation/reinspect")
async def remediation_reinspect(
    body: RemediationReinspectBody,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.remediation_reinspect(body=body)


@router.post("/remediation/close")
async def close_remediation(
    body: RemediationCloseBody,
    execution_service: ExecutionService = Depends(get_execution_service),
):
    return await execution_service.close_remediation(body=body)

"""Execution flow helpers used by routers and domain services."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.domain.execution.flows import (
    aggregate_provenance_chain,
    apply_variation,
    calc_inspection_frequency,
    close_remediation_trip,
    compute_did_reputation,
    execute_triprole_action,
    get_frequency_dashboard,
    get_full_lineage,
    ingest_sensor_data,
    open_remediation_trip,
    replay_offline_packets,
    record_lab_test,
    remediation_reinspect,
    scan_to_confirm_signature,
    trace_asset_origin,
    transfer_asset,
    verify_component_utxo,
)


def execute_triprole_action_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return execute_triprole_action(sb=sb, body=body)


def aggregate_provenance_chain_flow(*, utxo_id: str, sb: Client) -> dict[str, Any]:
    return aggregate_provenance_chain(utxo_id=utxo_id, sb=sb)


def get_full_lineage_flow(*, utxo_id: str, sb: Client) -> dict[str, Any]:
    return get_full_lineage(utxo_id=utxo_id, sb=sb)


def trace_asset_origin_flow(
    *,
    sb: Client,
    utxo_id: str = "",
    boq_item_uri: str = "",
    project_uri: str = "",
) -> dict[str, Any]:
    return trace_asset_origin(
        sb=sb,
        utxo_id=utxo_id,
        boq_item_uri=boq_item_uri,
        project_uri=project_uri,
    )


def did_reputation_flow(
    *,
    sb: Client,
    project_uri: str,
    participant_did: str,
    window_days: int = 90,
) -> dict[str, Any]:
    return compute_did_reputation(
        sb=sb,
        project_uri=project_uri,
        participant_did=participant_did,
        window_days=window_days,
    )


def transfer_asset_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return transfer_asset(
        sb=sb,
        item_id=str(body.item_id or ""),
        amount=float(body.amount),
        project_uri=str(body.project_uri or ""),
        executor_uri=str(body.executor_uri or "v://executor/system/"),
        executor_role=str(body.executor_role or "DOCPEG"),
        docpeg_proof_id=str(body.docpeg_proof_id or ""),
        docpeg_hash=str(body.docpeg_hash or ""),
        metadata=dict(body.metadata or {}),
    )


def verify_component_utxo_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return verify_component_utxo(sb=sb, body=body)


def apply_variation_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return apply_variation(
        sb=sb,
        boq_item_uri=str(body.boq_item_uri or ""),
        delta_amount=float(body.delta_amount),
        reason=str(body.reason or ""),
        project_uri=str(body.project_uri or ""),
        executor_uri=str(body.executor_uri or "v://executor/system/"),
        executor_did=str(body.executor_did or ""),
        executor_role=str(body.executor_role or "TRIPROLE"),
        metadata=dict(body.metadata or {}),
        credentials_vc=list(body.credentials_vc or []),
        geo_location=dict(body.geo_location or {}),
        server_timestamp_proof=dict(body.server_timestamp_proof or {}),
        offline_packet_id=str(body.offline_packet_id or ""),
    )


def replay_offline_packets_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    packets = [
        (item.model_dump() if hasattr(item, "model_dump") else dict(item))
        for item in list(body.packets or [])
    ]
    return replay_offline_packets(
        sb=sb,
        packets=packets,
        stop_on_error=bool(body.stop_on_error),
        default_executor_uri=str(body.default_executor_uri or "v://executor/system/"),
        default_executor_role=str(body.default_executor_role or "TRIPROLE"),
    )


def scan_confirm_signature_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return scan_to_confirm_signature(
        sb=sb,
        input_proof_id=str(body.input_proof_id or ""),
        scan_payload=str(body.scan_payload or ""),
        scanner_did=str(body.scanner_did or ""),
        scanner_role=str(body.scanner_role or "supervisor"),
        executor_uri=str(body.executor_uri or "v://executor/system/"),
        executor_role=str(body.executor_role or "SUPERVISOR"),
        signature_hash=str(body.signature_hash or ""),
        signer_metadata=dict(body.signer_metadata or {}),
        geo_location=dict(body.geo_location or {}),
        server_timestamp_proof=dict(body.server_timestamp_proof or {}),
    )


def ingest_sensor_data_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return ingest_sensor_data(
        sb=sb,
        device_id=str(body.device_id or ""),
        raw_payload=body.raw_payload,
        boq_item_uri=str(body.boq_item_uri or ""),
        project_uri=str(body.project_uri or "") or None,
        executor_uri=str(body.executor_uri or "v://executor/system/"),
        executor_did=str(body.executor_did or ""),
        executor_role=str(body.executor_role or "TRIPROLE"),
        metadata=dict(body.metadata or {}),
        credentials_vc=list(body.credentials_vc or []),
        geo_location=dict(body.geo_location or {}),
        server_timestamp_proof=dict(body.server_timestamp_proof or {}),
    )


def record_lab_test_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return record_lab_test(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        boq_item_uri=str(body.boq_item_uri or ""),
        sample_id=str(body.sample_id or ""),
        jtg_form_code=str(body.jtg_form_code or "JTG-E60"),
        instrument_sn=str(body.instrument_sn or ""),
        tested_at=str(body.tested_at or ""),
        witness_record=dict(body.witness_record or {}),
        sample_tracking=dict(body.sample_tracking or {}),
        metrics=list(body.metrics or []),
        result=str(body.result or ""),
        executor_uri=str(body.executor_uri or "v://executor/lab/system/"),
        metadata=dict(body.metadata or {}),
    )


def calc_inspection_frequency_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return calc_inspection_frequency(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        boq_item_uri=str(body.boq_item_uri or ""),
    )


def get_frequency_dashboard_flow(*, project_uri: str, limit_items: int, sb: Client) -> dict[str, Any]:
    return get_frequency_dashboard(
        sb=sb,
        project_uri=project_uri,
        limit_items=limit_items,
    )


def open_remediation_trip_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return open_remediation_trip(
        sb=sb,
        fail_proof_id=str(body.fail_proof_id or ""),
        notice=str(body.notice or ""),
        executor_uri=str(body.executor_uri or "v://executor/supervisor/system/"),
        due_date=str(body.due_date or ""),
        assignees=list(body.assignees or []),
    )


def remediation_reinspect_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return remediation_reinspect(
        sb=sb,
        remediation_proof_id=str(body.remediation_proof_id or ""),
        result=str(body.result or ""),
        payload=dict(body.payload or {}),
        executor_uri=str(body.executor_uri or "v://executor/inspector/system/"),
    )


def close_remediation_trip_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return close_remediation_trip(
        sb=sb,
        remediation_proof_id=str(body.remediation_proof_id or ""),
        reinspection_proof_id=str(body.reinspection_proof_id or ""),
        close_note=str(body.close_note or ""),
        executor_uri=str(body.executor_uri or "v://executor/supervisor/system/"),
    )

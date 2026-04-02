"""
TripRole lifecycle execution + provenance aggregation service.

Implements:
- TripRole action executor (quality.check / measure.record / variation.record / settlement.confirm)
- aggregate_provenance_chain(utxo_id)
- Gate locking for settlement (FAIL blocks unless compensated by VARIATION)
- DocFinal package builder by BOQ item URI
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.api.domain.utxo.integrations import ProofUTXOEngine
from services.api.domain.execution.triprole_common import (
    utc_iso as _utc_iso,
)
from services.api.domain.execution.triprole_lineage import (
    _item_no_from_boq_uri,
    _smu_id_from_item_no,
)
from services.api.domain.execution.triprole_lineage_entry import (
    aggregate_provenance_chain as _aggregate_provenance_chain_runtime,
    get_full_lineage as _get_full_lineage_runtime,
    trace_asset_origin as _trace_asset_origin_runtime,
)
from services.api.domain.execution.triprole_offline_entry import (
    replay_offline_packets as _replay_offline_packets_runtime,
)
from services.api.domain.execution.triprole_transfer import (
    transfer_asset as _transfer_asset,
)
from services.api.domain.execution.triprole_ingest import (
    ingest_sensor_data as _ingest_sensor_data,
)
from services.api.domain.execution.triprole_variation import (
    apply_variation as _apply_variation,
)
from services.api.domain.execution.triprole_action_entry import (
    execute_triprole_action as _execute_triprole_action_runtime,
)
from services.api.domain.execution.triprole_scan_confirm_entry import (
    scan_to_confirm_signature as _scan_to_confirm_signature_runtime,
)
from services.api.domain.execution.triprole_docfinal import (
    encrypt_aes256 as _encrypt_aes256,
)
from services.api.domain.execution.triprole_docfinal_export import (
    export_doc_final_archive as _export_doc_final_archive,
)
from services.api.domain.execution.triprole_docfinal_master_export import (
    export_doc_final as _export_doc_final_runtime,
)
from services.api.domain.execution.triprole_docfinal_package import (
    build_docfinal_package_for_boq as _build_docfinal_package_for_boq_runtime,
)
from services.api.domain.execution.triprole_realtime_entry import (
    get_boq_realtime_status as _get_boq_realtime_status_runtime,
)


VALID_TRIPROLE_ACTIONS = {
    "quality.check",
    "measure.record",
    "variation.record",
    "settlement.confirm",
    "dispute.resolve",
    "scan.entry",
    "meshpeg.verify",
    "formula.price",
    "gateway.sync",
}

CONSENSUS_REQUIRED_ROLES = ("contractor", "supervisor", "owner")


def aggregate_provenance_chain(utxo_id: str, sb: Any, *, max_depth: int = 256) -> dict[str, Any]:
    """
    Recursively aggregate lineage from root -> current UTXO and compute Total Proof Hash.
    """
    return _aggregate_provenance_chain_runtime(
        utxo_id=utxo_id,
        sb=sb,
        max_depth=max_depth,
    )


def aggregate_chain(utxo_id: str, sb: Any, *, max_depth: int = 256) -> dict[str, Any]:
    """
    Backward-compatible alias for aggregate_provenance_chain.
    """
    return aggregate_provenance_chain(utxo_id=utxo_id, sb=sb, max_depth=max_depth)


def get_full_lineage(utxo_id: str, sb: Any, *, max_depth: int = 256) -> dict[str, Any]:
    """
    Pull the full lineage payload for one BOQ asset branch:
    - all v://norm references
    - evidence photo hashes
    - QC conclusions by stage
    """
    return _get_full_lineage_runtime(
        utxo_id=utxo_id,
        sb=sb,
        max_depth=max_depth,
        aggregate_provenance_chain_fn=aggregate_provenance_chain,
    )


def trace_asset_origin(
    *,
    sb: Any,
    utxo_id: str = "",
    boq_item_uri: str = "",
    project_uri: str = "",
    max_depth: int = 512,
) -> dict[str, Any]:
    return _trace_asset_origin_runtime(
        sb=sb,
        utxo_id=utxo_id,
        boq_item_uri=boq_item_uri,
        project_uri=project_uri,
        max_depth=max_depth,
        get_boq_realtime_status_fn=lambda supabase, scoped_project, limit: get_boq_realtime_status(
            sb=supabase,
            project_uri=scoped_project,
            limit=limit,
        ),
    )


def transfer_asset(
    *,
    sb: Any,
    item_id: str,
    amount: float,
    executor_uri: str = "v://executor/system/",
    executor_role: str = "DOCPEG",
    docpeg_proof_id: str = "",
    docpeg_hash: str = "",
    metadata: dict[str, Any] | None = None,
    project_uri: str | None = None,
) -> dict[str, Any]:
    return _transfer_asset(
        sb=sb,
        item_id=item_id,
        amount=amount,
        executor_uri=executor_uri,
        executor_role=executor_role,
        docpeg_proof_id=docpeg_proof_id,
        docpeg_hash=docpeg_hash,
        metadata=metadata,
        project_uri=project_uri,
    )


def ingest_sensor_data(
    *,
    sb: Any,
    device_id: str,
    raw_payload: Any,
    boq_item_uri: str,
    project_uri: str | None = None,
    executor_uri: str = "v://executor/system/",
    executor_did: str = "",
    executor_role: str = "TRIPROLE",
    metadata: dict[str, Any] | None = None,
    credentials_vc: list[dict[str, Any]] | None = None,
    geo_location: dict[str, Any] | None = None,
    server_timestamp_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _ingest_sensor_data(
        sb=sb,
        device_id=device_id,
        raw_payload=raw_payload,
        boq_item_uri=boq_item_uri,
        project_uri=project_uri,
        executor_uri=executor_uri,
        executor_did=executor_did,
        executor_role=executor_role,
        metadata=metadata,
        credentials_vc=credentials_vc,
        geo_location=geo_location,
        server_timestamp_proof=server_timestamp_proof,
    )


def apply_variation(
    *,
    sb: Any,
    boq_item_uri: str,
    delta_amount: float,
    reason: str = "",
    project_uri: str | None = None,
    executor_uri: str = "v://executor/system/",
    executor_did: str = "",
    executor_role: str = "TRIPROLE",
    offline_packet_id: str = "",
    metadata: dict[str, Any] | None = None,
    credentials_vc: list[dict[str, Any]] | None = None,
    geo_location: dict[str, Any] | None = None,
    server_timestamp_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _apply_variation(
        sb=sb,
        boq_item_uri=boq_item_uri,
        delta_amount=delta_amount,
        reason=reason,
        project_uri=project_uri,
        executor_uri=executor_uri,
        executor_did=executor_did,
        executor_role=executor_role,
        offline_packet_id=offline_packet_id,
        metadata=metadata,
        credentials_vc=credentials_vc,
        geo_location=geo_location,
        server_timestamp_proof=server_timestamp_proof,
    )


def execute_triprole_action(*, sb: Any, body: Any) -> dict[str, Any]:
    """Execute a TripRole action over one input UTXO and create next-state UTXO."""
    return _execute_triprole_action_runtime(
        sb=sb,
        body=body,
        valid_actions=VALID_TRIPROLE_ACTIONS,
        consensus_required_roles=CONSENSUS_REQUIRED_ROLES,
        aggregate_provenance_chain_fn=aggregate_provenance_chain,
    )


def replay_offline_packets(
    *,
    sb: Any,
    packets: list[dict[str, Any]],
    stop_on_error: bool = False,
    default_executor_uri: str = "v://executor/system/",
    default_executor_role: str = "TRIPROLE",
) -> dict[str, Any]:
    return _replay_offline_packets_runtime(
        sb=sb,
        packets=packets,
        stop_on_error=stop_on_error,
        default_executor_uri=default_executor_uri,
        default_executor_role=default_executor_role,
        apply_variation_fn=apply_variation,
        execute_triprole_action_fn=execute_triprole_action,
    )


def scan_to_confirm_signature(
    *,
    sb: Any,
    input_proof_id: str,
    scan_payload: Any,
    scanner_did: str,
    scanner_role: str,
    executor_uri: str = "v://executor/system/",
    executor_role: str = "SUPERVISOR",
    signature_hash: str = "",
    signer_metadata: dict[str, Any] | None = None,
    geo_location: dict[str, Any] | None = None,
    server_timestamp_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _scan_to_confirm_signature_runtime(
        sb=sb,
        input_proof_id=input_proof_id,
        scan_payload=scan_payload,
        scanner_did=scanner_did,
        scanner_role=scanner_role,
        executor_uri=executor_uri,
        executor_role=executor_role,
        signature_hash=signature_hash,
        signer_metadata=signer_metadata,
        geo_location=geo_location,
        server_timestamp_proof=server_timestamp_proof,
        consensus_required_roles=CONSENSUS_REQUIRED_ROLES,
    )


def build_docfinal_package_for_boq(
    *,
    boq_item_uri: str,
    sb: Any,
    project_meta: dict[str, Any] | None = None,
    verify_base_url: str = "https://verify.qcspec.com",
    template_path: str | Path | None = None,
    apply_asset_transfer: bool = False,
    transfer_amount: float | None = None,
    transfer_executor_uri: str = "v://executor/system/",
    aggregate_anchor_code: str = "",
    aggregate_direction: str = "all",
    aggregate_level: str = "all",
) -> dict[str, Any]:
    return _build_docfinal_package_for_boq_runtime(
        boq_item_uri=boq_item_uri,
        sb=sb,
        project_meta=project_meta,
        verify_base_url=verify_base_url,
        template_path=template_path,
        apply_asset_transfer=apply_asset_transfer,
        transfer_amount=transfer_amount,
        transfer_executor_uri=transfer_executor_uri,
        aggregate_anchor_code=aggregate_anchor_code,
        aggregate_direction=aggregate_direction,
        aggregate_level=aggregate_level,
        module_file=__file__,
        get_boq_realtime_status_fn=get_boq_realtime_status,
        get_full_lineage_fn=get_full_lineage,
        trace_asset_origin_fn=trace_asset_origin,
        transfer_asset_fn=transfer_asset,
    )


def get_boq_realtime_status(
    *,
    sb: Any,
    project_uri: str,
    limit: int = 2000,
) -> dict[str, Any]:
    return _get_boq_realtime_status_runtime(
        sb=sb,
        project_uri=project_uri,
        limit=limit,
        aggregate_provenance_chain_fn=lambda utxo_id: aggregate_provenance_chain(utxo_id, sb),
    )


def export_doc_final(
    *,
    sb: Any,
    project_uri: str,
    project_name: str | None = None,
    passphrase: str = "",
    verify_base_url: str = "https://verify.qcspec.com",
    include_unsettled: bool = False,
) -> dict[str, Any]:
    return _export_doc_final_runtime(
        sb=sb,
        project_uri=project_uri,
        project_name=project_name,
        passphrase=passphrase,
        verify_base_url=verify_base_url,
        include_unsettled=include_unsettled,
        get_boq_realtime_status_fn=get_boq_realtime_status,
        proof_utxo_engine_cls=ProofUTXOEngine,
        export_doc_final_archive_fn=_export_doc_final_archive,
        build_docfinal_package_for_boq_fn=build_docfinal_package_for_boq,
        get_full_lineage_fn=get_full_lineage,
        item_no_from_boq_uri_fn=_item_no_from_boq_uri,
        smu_id_from_item_no_fn=_smu_id_from_item_no,
        utc_iso_fn=_utc_iso,
        encrypt_aes256_fn=_encrypt_aes256,
    )

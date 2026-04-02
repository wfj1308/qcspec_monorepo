"""Scan-confirm entry wiring."""

from __future__ import annotations

from typing import Any

from services.api.domain.execution.triprole_scan_confirm import (
    execute_scan_confirm_signature as _execute_scan_confirm_signature,
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
    consensus_required_roles: tuple[str, ...] = ("contractor", "supervisor", "owner"),
) -> dict[str, Any]:
    return _execute_scan_confirm_signature(
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
        consensus_required_roles=consensus_required_roles,
    )

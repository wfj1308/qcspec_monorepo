"""Shared helper functions for SMU execution/signing flows."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from fastapi import HTTPException
from services.api.domain.execution.flows import execute_triprole_action
from services.api.domain.smu.runtime.smu_primitives import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_float as _to_float,
    to_text as _to_text,
)


def collect_qc_values(measurement_data: dict[str, Any]) -> list[float]:
    values_for_qc: list[float] = []
    for candidate in _as_list(measurement_data.get("values")):
        parsed = _to_float(candidate)
        if parsed is not None:
            values_for_qc.append(float(parsed))
    if values_for_qc:
        return values_for_qc
    raw_values = _to_text(measurement_data.get("values") or "").strip()
    if not raw_values:
        return values_for_qc
    for part in re.split(r"[,，;\s\n]+", raw_values):
        parsed = _to_float(part)
        if parsed is not None:
            values_for_qc.append(float(parsed))
    return values_for_qc


def resolve_single_value(measurement_data: dict[str, Any]) -> float | None:
    single_value = _to_float(measurement_data.get("value"))
    if single_value is None:
        single_value = _to_float(measurement_data.get("measured_value"))
    if single_value is None:
        single_value = _to_float(measurement_data.get("claim_quantity"))
    return single_value


def build_quality_payload(
    *,
    component_type: str,
    measurement_data: dict[str, Any],
    snappeg_hash: str,
    values_for_qc: list[float],
    single_value: float | None,
    contract_formula_ok: bool,
) -> dict[str, Any]:
    quality_payload: dict[str, Any] = {
        "component_type": component_type,
        "measurement": measurement_data,
        "snappeg_payload_hash": snappeg_hash,
    }
    if values_for_qc:
        quality_payload["values"] = values_for_qc
    if single_value is not None:
        quality_payload["value"] = float(single_value)
    if contract_formula_ok:
        quality_payload["result_policy"] = "contract_formula_pass"
    return quality_payload


def build_signatures(
    *,
    input_proof_id: str,
    now_iso: str,
    contractor_did: str,
    supervisor_did: str,
    owner_did: str,
) -> list[dict[str, Any]]:
    signatures: list[dict[str, Any]] = []
    for role, did in (
        ("contractor", contractor_did),
        ("supervisor", supervisor_did),
        ("owner", owner_did),
    ):
        normalized_did = _to_text(did).strip()
        if not normalized_did.startswith("did:"):
            raise HTTPException(400, f"{role}_did must start with did:")
        sig = hashlib.sha256(f"{input_proof_id}|{normalized_did}|{role}|{now_iso}".encode("utf-8")).hexdigest()
        signatures.append({"role": role, "did": normalized_did, "signature_hash": sig, "signed_at": now_iso})
    return signatures


def resolve_signer_metadata(
    *,
    signer_metadata: dict[str, Any],
    now_iso: str,
    contractor_did: str,
    supervisor_did: str,
    owner_did: str,
) -> dict[str, Any]:
    biometric = _as_dict(signer_metadata)
    if biometric:
        return biometric
    return {
        "mode": "liveness",
        "passed": True,
        "checked_at": now_iso,
        "device": "mobile",
        "signers": [
            {"role": "contractor", "did": contractor_did, "biometric_ok": True},
            {"role": "supervisor", "did": supervisor_did, "biometric_ok": True},
            {"role": "owner", "did": owner_did, "biometric_ok": True},
        ],
    }


def build_approval_payload(
    *,
    consensus_values: list[dict[str, Any]] | None,
    allowed_deviation: float | None,
    allowed_deviation_percent: float | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "approved_from": "SMU_APPROVAL_PANEL",
        "status_target": "Approved",
    }
    if consensus_values:
        payload["consensus_values"] = consensus_values
    if allowed_deviation is not None:
        payload["allowed_deviation"] = allowed_deviation
    if allowed_deviation_percent is not None:
        payload["allowed_deviation_percent"] = allowed_deviation_percent
    return payload


def build_sign_inputs(
    *,
    in_id: str,
    now_iso: str,
    contractor_did: str,
    supervisor_did: str,
    owner_did: str,
    signer_metadata: dict[str, Any],
    consensus_values: list[dict[str, Any]] | None,
    allowed_deviation: float | None,
    allowed_deviation_percent: float | None,
) -> dict[str, Any]:
    signatures = build_signatures(
        input_proof_id=in_id,
        now_iso=now_iso,
        contractor_did=contractor_did,
        supervisor_did=supervisor_did,
        owner_did=owner_did,
    )
    biometric = resolve_signer_metadata(
        signer_metadata=signer_metadata,
        now_iso=now_iso,
        contractor_did=contractor_did,
        supervisor_did=supervisor_did,
        owner_did=owner_did,
    )
    approval_payload = build_approval_payload(
        consensus_values=consensus_values,
        allowed_deviation=allowed_deviation,
        allowed_deviation_percent=allowed_deviation_percent,
    )
    return {
        "signatures": signatures,
        "biometric": biometric,
        "approval_payload": approval_payload,
    }


def run_settlement_confirm(
    *,
    sb: Any,
    in_id: str,
    item_uri: str,
    supervisor_executor_uri: str,
    supervisor_did: str,
    signatures: list[dict[str, Any]],
    signer_metadata: dict[str, Any],
    payload: dict[str, Any],
    geo_location: dict[str, Any],
    server_timestamp_proof: dict[str, Any],
) -> dict[str, Any]:
    return _as_dict(
        execute_triprole_action(
            sb=sb,
            body={
                "action": "settlement.confirm",
                "input_proof_id": in_id,
                "executor_uri": supervisor_executor_uri,
                "executor_did": supervisor_did,
                "executor_role": "SUPERVISOR",
                "boq_item_uri": item_uri,
                "result": "PASS",
                "signatures": signatures,
                "consensus_signatures": signatures,
                "signer_metadata": signer_metadata,
                "payload": payload,
                "geo_location": geo_location,
                "server_timestamp_proof": server_timestamp_proof,
            },
        )
    )


def run_execute_actions(
    *,
    sb: Any,
    in_id: str,
    item_uri: str,
    executor_uri: str,
    executor_did: str,
    executor_role: str,
    force_reject: bool,
    force_pass: bool,
    quality_payload: dict[str, Any],
    credentials_vc: list[dict[str, Any]],
    geo_location: dict[str, Any],
    server_timestamp_proof: dict[str, Any],
    component_type: str,
    measurement_data: dict[str, Any],
    snappeg_hash: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    override_result = "FAIL" if bool(force_reject) else ("PASS" if bool(force_pass) else "")
    qc = execute_triprole_action(
        sb=sb,
        body={
            "action": "quality.check",
            "input_proof_id": in_id,
            "executor_uri": executor_uri,
            "executor_did": executor_did,
            "executor_role": executor_role,
            "boq_item_uri": item_uri,
            **({"result": override_result} if override_result else {}),
            "payload": quality_payload,
            "credentials_vc": credentials_vc,
            "geo_location": geo_location,
            "server_timestamp_proof": server_timestamp_proof,
        },
    )
    current = dict(qc)
    if (not force_reject) and _to_text(qc.get("result") or "").strip().upper() == "PASS":
        current = execute_triprole_action(
            sb=sb,
            body={
                "action": "measure.record",
                "input_proof_id": _to_text(qc.get("output_proof_id") or "").strip(),
                "executor_uri": executor_uri,
                "executor_did": executor_did,
                "executor_role": executor_role,
                "boq_item_uri": item_uri,
                "payload": {
                    "component_type": component_type,
                    "measurement": measurement_data,
                    "snappeg_payload_hash": snappeg_hash,
                },
                "credentials_vc": credentials_vc,
                "geo_location": geo_location,
                "server_timestamp_proof": server_timestamp_proof,
            },
        )
    return _as_dict(qc), _as_dict(current)


__all__ = [
    "build_approval_payload",
    "build_sign_inputs",
    "build_quality_payload",
    "build_signatures",
    "collect_qc_values",
    "resolve_signer_metadata",
    "resolve_single_value",
    "run_execute_actions",
    "run_settlement_confirm",
]


"""Reference resolution helpers for SpecIR ref-only linkage."""

from __future__ import annotations

from typing import Any


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _normalize_unit(value: Any) -> str:
    return _to_text(value).strip().lower()


def _meter_rule_uri_from_unit(unit: str, fallback_token: str) -> str:
    normalized_unit = _normalize_unit(unit)
    if normalized_unit in {"m3", "m^3"}:
        return "v://norm/meter-rule/by-volume@v1"
    if normalized_unit in {"m2", "m^2"}:
        return "v://norm/meter-rule/by-area@v1"
    if normalized_unit in {"t", "ton", "kg"}:
        return "v://norm/meter-rule/by-weight@v1"
    if fallback_token == "raft-foundation":
        return "v://norm/meter-rule/by-volume@v1"
    return f"v://norm/meter-rule/{fallback_token}@v1"


def resolve_spu_ref_pack(
    *,
    item_code: str = "",
    item_name: str = "",
    quantity_unit: str = "",
    template_id: str = "",
) -> dict[str, str]:
    code = _to_text(item_code).strip()
    prefix = code.split("-")[0] if code else ""
    name = _to_text(item_name).strip().lower()
    template = _to_text(template_id).strip().lower().replace("_", "-")

    token = "pavement-laying"
    if "raft" in name or "筏" in name or template in {"spu-raft-foundation", "raft-foundation"}:
        token = "raft-foundation"
    elif prefix in {"101", "102"} or template == "spu-contract" or "contract" in name:
        token = "contract-payment"
    elif prefix == "403" or template == "spu-reinforcement" or "rebar" in name:
        token = "rebar-processing"
    elif prefix in {"401", "405"} or template in {"spu-bridge", "spu-concrete", "spu-capbeam", "spu-pilefoundation"}:
        token = "pier-concrete-casting"
    elif prefix == "702" or template == "spu-landscape" or "landscape" in name:
        token = "landscape-work"
    elif prefix == "600" or template == "spu-physical" or "pavement" in name:
        token = "pavement-laying"

    if token == "raft-foundation":
        ref_spu_uri = "v://normref.com/spu/raft-foundation@v1"
        ref_quota_uri = "v://normref.com/quota/raft-foundation@v1"
    else:
        ref_spu_uri = f"v://norm/spu/{token}@v1"
        ref_quota_uri = f"v://norm/quota/{token}@v1"
    ref_meter_rule_uri = _meter_rule_uri_from_unit(quantity_unit, token)
    return {
        "ref_spu_uri": ref_spu_uri,
        "ref_quota_uri": ref_quota_uri,
        "ref_meter_rule_uri": ref_meter_rule_uri,
    }


__all__ = ["resolve_spu_ref_pack"]

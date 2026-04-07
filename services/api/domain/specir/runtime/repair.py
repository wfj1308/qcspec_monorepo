"""Repair helpers for SpecIR reference consistency."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from services.api.domain.specir.runtime.registry import (
    ensure_specir_object,
)
from services.api.domain.specir.runtime.spu_schema import build_spu_ultimate_content


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def infer_specir_kind(uri: str) -> str:
    normalized = _to_text(uri).strip()
    if normalized.startswith("v://norm/gate/"):
        return "gate"
    if normalized.startswith("v://norm/spec-rule/"):
        return "spec_rule"
    if normalized.startswith("v://norm/specdict/") and "#" in normalized:
        return "spec_item"
    if normalized.startswith("v://norm/specdict/"):
        return "spec_dict"
    if normalized.startswith("v://norm/spu/"):
        return "spu"
    if normalized.startswith("v://norm/quota/"):
        return "quota"
    if normalized.startswith("v://norm/meter-rule/"):
        return "meter_rule"
    if normalized.startswith("v://norm/"):
        return "spec_ref"
    return "unknown"


def collect_ref_uris_from_state_data(state_data: dict[str, Any]) -> list[str]:
    sd = _as_dict(state_data)
    uris: set[str] = set()
    for key in (
        "ref_gate_uri",
        "ref_spec_uri",
        "ref_spec_dict_uri",
        "ref_spec_item_uri",
        "ref_spu_uri",
        "ref_quota_uri",
        "ref_meter_rule_uri",
        "ref_spu",
        "ref_quota",
        "ref_meter_rule",
    ):
        uri = _to_text(sd.get(key) or "").strip()
        if uri.startswith("v://"):
            uris.add(uri)
    for raw in _as_list(sd.get("ref_gate_uris")):
        uri = _to_text(raw).strip()
        if uri.startswith("v://"):
            uris.add(uri)
    return sorted(uris)


def _content_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def register_missing_specir_refs_from_rows(
    *,
    sb: Any,
    rows: list[dict[str, Any]],
    source: str = "proof_utxo_ref_scan",
) -> dict[str, Any]:
    checked = 0
    saved: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        state_data = _as_dict(_as_dict(row).get("state_data"))
        for uri in collect_ref_uris_from_state_data(state_data):
            if uri in seen:
                continue
            seen.add(uri)
            checked += 1
            kind = infer_specir_kind(uri)
            if kind == "spu":
                content = build_spu_ultimate_content(
                    spu_uri=uri,
                    title=uri.rsplit("/", 1)[-1].split("@", 1)[0],
                    content={
                        "industry": "Highway",
                        "unit": "",
                        "measure_statement": "Auto-registered by SpecIR repair; refine before production use.",
                        "measure_operator": "auto-register-placeholder",
                        "measure_expression": "approved_quantity",
                        "quota_ref": "",
                        "meter_rule_ref": "",
                        "gate_refs": [],
                    },
                )
            else:
                content = {"auto_registered": True, "source": source, "uri": uri}
            try:
                result = ensure_specir_object(
                    sb=sb,
                    uri=uri,
                    kind=kind,
                    title=uri.rsplit("/", 1)[-1].split("@", 1)[0],
                    content=content,
                    metadata={
                        "source": source,
                        "uri": uri,
                        "kind": kind,
                        "content_hash": _content_hash(content),
                    },
                    status="active",
                )
                if bool(result.get("ok")):
                    saved.append({"uri": uri, "kind": kind})
                else:
                    errors.append({"uri": uri, "kind": kind, "error": _to_text(result.get("error") or "unknown").strip()})
            except Exception as exc:
                errors.append({"uri": uri, "kind": kind, "error": f"{exc.__class__.__name__}: {exc}"})
    return {
        "ok": len(errors) == 0,
        "checked_count": checked,
        "saved_count": len(saved),
        "error_count": len(errors),
        "saved": saved,
        "errors": errors,
    }


__all__ = [
    "collect_ref_uris_from_state_data",
    "infer_specir_kind",
    "register_missing_specir_refs_from_rows",
]

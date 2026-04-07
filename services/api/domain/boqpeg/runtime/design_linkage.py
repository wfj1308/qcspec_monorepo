"""Design parser + BOQ linkage engines for design/BOQ/proof bidirectional closure."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import io
import json
import os
import re
import tempfile
from typing import Any

from fastapi import HTTPException

from services.api.core.norm.normpeg_engine import resolve_norm_rule
from services.api.domain.boqpeg.runtime.parser import parse_boq_upload
from services.api.domain.utxo.integrations import ProofUTXOEngine

_STATION_PATTERN = re.compile(r"\b(?:[A-Za-z]{0,3})\d+\+\d+(?:\.\d+)?\b")
_MATERIAL_PATTERN = re.compile(r"\b(?:C\d{2,3}|HRB\d{3}|HPB\d{3}|Q\d{3}[A-Z]?|P\.O\s?\d{2}\.\d)\b", re.IGNORECASE)
_NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?")
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]+")

_KIND_KEYWORDS: dict[str, tuple[str, ...]] = {
    "beam": ("beam", "girder", "梁"),
    "column": ("column", "柱"),
    "slab": ("slab", "板"),
    "pile": ("pile", "桩"),
    "wall": ("wall", "墙"),
    "pier": ("pier", "墩"),
    "cap": ("cap", "承台"),
}


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    text = _to_text(value).strip().replace(",", "")
    if not text:
        return float(default)
    try:
        return float(text)
    except Exception:
        match = _NUMBER_PATTERN.search(text)
        if not match:
            return float(default)
        try:
            return float(match.group(0))
        except Exception:
            return float(default)


def _round(value: float, ndigits: int = 6) -> float:
    return round(float(value), ndigits)


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN_PATTERN.findall(_to_text(text).lower()) if token.strip()}


def _sha16(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _guess_component_kind(text: str) -> str:
    blob = _to_text(text).lower()
    for kind, keywords in _KIND_KEYWORDS.items():
        if any(keyword.lower() in blob for keyword in keywords):
            return kind
    return "component"


def _extract_station(text: str) -> str:
    match = _STATION_PATTERN.search(_to_text(text))
    return match.group(0) if match else ""


def _extract_material(text: str) -> str:
    match = _MATERIAL_PATTERN.search(_to_text(text))
    return match.group(0) if match else ""


def _extract_ifc_components(content: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    components: list[dict[str, Any]] = []
    try:
        import ifcopenshell  # type: ignore
    except Exception:
        warnings.append("ifcopenshell not installed; using text fallback parser for IFC.")
        return components, warnings

    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as f:
            f.write(content)
            tmp_path = f.name
        model = ifcopenshell.open(tmp_path)
        element_types = ("IfcBeam", "IfcColumn", "IfcSlab", "IfcPile", "IfcWall", "IfcMember")
        for etype in element_types:
            for index, obj in enumerate(model.by_type(etype), start=1):
                gid = _to_text(getattr(obj, "GlobalId", "")).strip()
                name = _to_text(getattr(obj, "Name", "")).strip()
                obj_type = _to_text(getattr(obj, "ObjectType", "")).strip()
                label = name or obj_type or etype
                component_id = gid or f"{etype.lower()}-{index}"
                components.append(
                    {
                        "component_id": component_id,
                        "component_type": etype.replace("Ifc", "").lower(),
                        "description": label,
                        "material_spec": "",
                        "location_mark": "",
                        "geometry": {
                            "quantity": 1.0,
                            "length": None,
                            "section": "",
                        },
                        "source": {"ifc_type": etype, "global_id": gid},
                    }
                )
        if not components:
            warnings.append("IFC parsed but no target structural entities were found.")
    except Exception as exc:
        warnings.append(f"ifc parse failed: {exc}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    return components, warnings


def _extract_pdf_text(content: bytes) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        import pdfplumber  # type: ignore

        texts: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = _to_text(page.extract_text()).strip()
                if text:
                    texts.append(text)
        if texts:
            return "\n".join(texts), warnings
    except Exception as exc:
        warnings.append(f"pdfplumber parse fallback: {exc}")

    try:
        text = content.decode("utf-8", errors="replace")
        return text, warnings
    except Exception:
        return "", warnings


def _extract_text_components(text: str) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    lines = [line.strip() for line in _to_text(text).splitlines() if line.strip()]
    for index, line in enumerate(lines, start=1):
        kind = _guess_component_kind(line)
        material = _extract_material(line)
        station = _extract_station(line)
        numbers = [float(x) for x in _NUMBER_PATTERN.findall(line)]
        quantity = numbers[-1] if numbers else 1.0
        if quantity <= 0:
            quantity = 1.0
        component_id = f"{kind}-{_sha16(line)[:10]}-{index}"
        components.append(
            {
                "component_id": component_id,
                "component_type": kind,
                "description": line[:160],
                "material_spec": material,
                "location_mark": station,
                "geometry": {
                    "quantity": _round(quantity, 6),
                    "length": _round(numbers[0], 6) if numbers else None,
                    "section": "",
                },
                "source": {"line_index": index},
            }
        )
    return components


def parse_design_manifest_from_upload(
    *,
    upload_file_name: str,
    upload_content: bytes,
    project_uri: str,
    design_root_uri: str = "",
) -> dict[str, Any]:
    if not upload_content:
        raise HTTPException(400, "design file is empty")
    p_uri = _to_text(project_uri).strip()
    if not p_uri:
        raise HTTPException(400, "project_uri is required")
    name = _to_text(upload_file_name).strip() or "design.dat"
    lower = name.lower()
    warnings: list[str] = []
    components: list[dict[str, Any]] = []
    source_format = "unknown"

    if lower.endswith(".ifc"):
        source_format = "ifc"
        ifc_components, ifc_warnings = _extract_ifc_components(upload_content)
        components.extend(ifc_components)
        warnings.extend(ifc_warnings)
        if not components:
            fallback = _extract_text_components(_to_text(upload_content))
            components.extend(fallback)
    elif lower.endswith(".pdf"):
        source_format = "pdf"
        pdf_text, pdf_warnings = _extract_pdf_text(upload_content)
        warnings.extend(pdf_warnings)
        components.extend(_extract_text_components(pdf_text))
    elif lower.endswith(".dwg"):
        source_format = "dwg"
        warnings.append("DWG direct parsing is limited; recommend converting DWG to IFC/PDF first.")
        components.extend(_extract_text_components(_to_text(upload_content)))
    else:
        source_format = lower.split(".")[-1] if "." in lower else "text"
        components.extend(_extract_text_components(_to_text(upload_content)))

    root_uri = _to_text(design_root_uri).strip() or f"{p_uri.rstrip('/')}/design"
    normalized_components: list[dict[str, Any]] = []
    for comp in components:
        component_id = _to_text(comp.get("component_id")).strip() or f"component-{_sha16(json.dumps(comp, ensure_ascii=False))[:10]}"
        uri = f"{root_uri.rstrip('/')}/component/{component_id}"
        normalized_components.append(
            {
                **comp,
                "component_id": component_id,
                "component_uri": uri,
            }
        )

    raw_hash = hashlib.sha256(upload_content).hexdigest()
    manifest_uri = f"{root_uri.rstrip('/')}/manifest/{raw_hash[:16]}"
    return {
        "ok": True,
        "manifest": {
            "manifest_uri": manifest_uri,
            "project_uri": p_uri,
            "source": {
                "file_name": name,
                "format": source_format,
                "sha256": raw_hash,
                "parsed_at": datetime.now(UTC).isoformat(),
            },
            "components": normalized_components,
            "stats": {
                "component_count": len(normalized_components),
                "with_material_spec": sum(1 for x in normalized_components if _to_text(x.get("material_spec")).strip()),
                "with_location_mark": sum(1 for x in normalized_components if _to_text(x.get("location_mark")).strip()),
            },
            "warnings": warnings,
        },
    }


def _resolve_component_quantity(component: dict[str, Any]) -> float:
    geo = component.get("geometry") if isinstance(component.get("geometry"), dict) else {}
    for key in ("quantity", "count", "volume", "area", "length"):
        value = _to_float((geo or {}).get(key), default=-1.0)
        if value > 0:
            return value
    return 1.0


def _match_score(boq_code: str, boq_desc: str, boq_hierarchy: str, component: dict[str, Any]) -> float:
    score = 0.0
    comp_id = _to_text(component.get("component_id")).strip().lower()
    comp_desc = _to_text(component.get("description")).strip().lower()
    comp_kind = _to_text(component.get("component_type")).strip().lower()
    comp_mat = _to_text(component.get("material_spec")).strip().lower()
    comp_loc = _to_text(component.get("location_mark")).strip().lower()
    boq_code_lower = _to_text(boq_code).strip().lower()
    if boq_code_lower and (boq_code_lower in comp_id or comp_id in boq_code_lower):
        score += 0.55
    boq_prefix = boq_code_lower.split("-")[0] if boq_code_lower else ""
    if boq_prefix and boq_prefix in comp_desc:
        score += 0.1

    boq_tokens = _tokens(boq_desc) | _tokens(boq_hierarchy)
    comp_tokens = _tokens(comp_desc) | _tokens(comp_kind) | _tokens(comp_mat) | _tokens(comp_loc)
    if boq_tokens and comp_tokens:
        overlap = boq_tokens & comp_tokens
        union = boq_tokens | comp_tokens
        score += 0.35 * (len(overlap) / max(len(union), 1))

    boq_station = _extract_station(boq_desc + " " + boq_hierarchy).lower()
    if boq_station and boq_station == comp_loc:
        score += 0.2
    return score


def _create_proof(
    *,
    sb: Any,
    commit: bool,
    proof_id: str,
    owner_uri: str,
    project_uri: str,
    result: str,
    segment_uri: str,
    state_data: dict[str, Any],
) -> dict[str, Any]:
    preview = {
        "proof_id": proof_id,
        "result": result,
        "segment_uri": segment_uri,
        "state_data": state_data,
        "committed": False,
    }
    if not commit or sb is None:
        return preview
    row = ProofUTXOEngine(sb).create(
        proof_id=proof_id,
        owner_uri=owner_uri,
        project_uri=project_uri,
        proof_type="inspection",
        result=result,
        state_data=state_data,
        norm_uri="v://norm/NormPeg/DesignBOQLink/1.0",
        segment_uri=segment_uri,
        signer_uri=owner_uri,
        signer_role="SYSTEM",
    )
    return {
        **preview,
        "committed": True,
        "row": row,
    }


def _resolve_threshold_ratios(
    *,
    threshold_spec_uri: str,
    warning_ratio: float,
    review_ratio: float,
) -> tuple[float, float]:
    uri = _to_text(threshold_spec_uri).strip()
    if not uri:
        return warning_ratio, review_ratio
    try:
        payload = resolve_norm_rule(uri, {})
    except Exception:
        return warning_ratio, review_ratio
    data = payload if isinstance(payload, dict) else {}
    warn = _to_float(data.get("warning_ratio"), warning_ratio)
    if warn <= 0 or warn >= 1:
        warn = warning_ratio
    review = _to_float(data.get("review_ratio"), review_ratio)
    if review <= warn or review >= 1:
        review = review_ratio
    return warn, review


def match_boq_with_design_manifest(
    *,
    sb: Any,
    upload_file_name: str,
    upload_content: bytes,
    project_uri: str,
    owner_uri: str,
    design_manifest: dict[str, Any],
    deviation_warning_ratio: float = 0.03,
    deviation_review_ratio: float = 0.08,
    threshold_spec_uri: str = "",
    commit: bool = False,
) -> dict[str, Any]:
    boq_items = parse_boq_upload(upload_file_name, upload_content)
    manifest = design_manifest.get("manifest") if isinstance(design_manifest.get("manifest"), dict) else design_manifest
    components = manifest.get("components") if isinstance(manifest.get("components"), list) else []

    matches: list[dict[str, Any]] = []
    deviation_rows: list[dict[str, Any]] = []
    unmatched_rows: list[dict[str, Any]] = []
    component_index: dict[str, dict[str, Any]] = {}
    review_trips: list[dict[str, Any]] = []
    proofs: list[dict[str, Any]] = []

    for comp in components:
        if not isinstance(comp, dict):
            continue
        comp_uri = _to_text(comp.get("component_uri")).strip()
        if not comp_uri:
            continue
        component_index[comp_uri] = {
            "component_utxo_id": f"COMPU-{_sha16(comp_uri).upper()}",
            "component_uri": comp_uri,
            "component_id": _to_text(comp.get("component_id")).strip(),
            "component_type": _to_text(comp.get("component_type")).strip(),
            "material_spec": _to_text(comp.get("material_spec")).strip(),
            "location_mark": _to_text(comp.get("location_mark")).strip(),
            "geometry": comp.get("geometry") if isinstance(comp.get("geometry"), dict) else {},
            "matched_boq_codes": [],
            "status": "unmatched",
        }

    normalized_project_uri = _to_text(project_uri).strip()
    normalized_owner = _to_text(owner_uri).strip() or f"{normalized_project_uri.rstrip('/')}/role/system/"
    warning_ratio, review_ratio = _resolve_threshold_ratios(
        threshold_spec_uri=threshold_spec_uri,
        warning_ratio=deviation_warning_ratio,
        review_ratio=deviation_review_ratio,
    )

    for boq in boq_items:
        boq_qty = boq.approved_quantity if boq.approved_quantity is not None else boq.design_quantity
        boq_qty_value = _to_float(boq_qty, default=0.0)
        best_score = -1.0
        best_component: dict[str, Any] | None = None
        for comp in components:
            if not isinstance(comp, dict):
                continue
            score = _match_score(boq.item_no, boq.name, boq.hierarchy_raw, comp)
            if score > best_score:
                best_score = score
                best_component = comp

        if not best_component or best_score < 0.3:
            unmatched_rows.append(
                {
                    "boq_code": boq.item_no,
                    "boq_description": boq.name,
                    "reason": "no_component_match",
                }
            )
            continue

        comp_uri = _to_text(best_component.get("component_uri")).strip()
        design_qty = _resolve_component_quantity(best_component)
        base = max(abs(boq_qty_value), 1e-9)
        deviation_ratio = abs(boq_qty_value - design_qty) / base
        status = "consistent"
        if deviation_ratio > review_ratio:
            status = "deviation"
        elif deviation_ratio > warning_ratio:
            status = "warning"

        row = {
            "boq_code": boq.item_no,
            "boq_description": boq.name,
            "boq_unit": boq.unit,
            "boq_quantity": _round(boq_qty_value, 6),
            "component_uri": comp_uri,
            "component_id": _to_text(best_component.get("component_id")).strip(),
            "component_type": _to_text(best_component.get("component_type")).strip(),
            "design_quantity": _round(design_qty, 6),
            "deviation_ratio": _round(deviation_ratio, 6),
            "status": status,
            "score": _round(best_score, 6),
        }
        matches.append(row)
        if status != "consistent":
            deviation_rows.append(row)
        comp_state = component_index.get(comp_uri)
        if comp_state is not None:
            comp_state["matched_boq_codes"].append(boq.item_no)
            comp_state["status"] = "review" if status == "deviation" else "linked"

        proof_kind = "Design-BOQ Match Proof" if status in {"consistent", "warning"} else "Deviation Proof"
        proof_result = "FAIL" if status == "deviation" else "PASS"
        pid = f"GP-DBM-{_sha16(f'{normalized_project_uri}:{boq.item_no}:{comp_uri}:{status}').upper()}"
        segment_uri = f"{normalized_project_uri.rstrip('/')}/design-boq/{boq.item_no}"
        proof_state = {
            "proof_kind": proof_kind,
            "status": status,
            "boq_code": boq.item_no,
            "boq_description": boq.name,
            "component_uri": comp_uri,
            "component_type": _to_text(best_component.get("component_type")).strip(),
            "deviation_ratio": _round(deviation_ratio, 6),
            "design_quantity": _round(design_qty, 6),
            "boq_quantity": _round(boq_qty_value, 6),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        proofs.append(
            _create_proof(
                sb=sb,
                commit=bool(commit),
                proof_id=pid,
                owner_uri=normalized_owner,
                project_uri=normalized_project_uri,
                result=proof_result,
                segment_uri=segment_uri,
                state_data=proof_state,
            )
        )
        if status == "deviation":
            trip_id = f"TRIP-REVIEW-{_sha16(pid).upper()}"
            trip = {
                "trip_id": trip_id,
                "node_uri": comp_uri or segment_uri,
                "trigger": "design_boq_deviation_over_threshold",
                "deviation_ratio": _round(deviation_ratio, 6),
                "status": "PENDING_REVIEW",
            }
            review_trips.append(trip)
            proofs.append(
                _create_proof(
                    sb=sb,
                    commit=bool(commit),
                    proof_id=f"GP-DEVTRIP-{_sha16(trip_id).upper()}",
                    owner_uri=normalized_owner,
                    project_uri=normalized_project_uri,
                    result="OBSERVE",
                    segment_uri=f"{normalized_project_uri.rstrip('/')}/design-boq/review-trip/{boq.item_no}",
                    state_data={
                        "proof_kind": "Deviation Review Trip Trigger",
                        "trip": trip,
                        "generated_at": datetime.now(UTC).isoformat(),
                    },
                )
            )

    component_utxos = list(component_index.values())
    consistent_count = sum(1 for x in matches if x.get("status") == "consistent")
    warning_count = sum(1 for x in matches if x.get("status") == "warning")
    deviation_count = sum(1 for x in matches if x.get("status") == "deviation")

    return {
        "ok": True,
        "project_uri": normalized_project_uri,
        "manifest_uri": _to_text((manifest or {}).get("manifest_uri")).strip(),
        "summary": {
            "boq_rows": len(boq_items),
            "matched_rows": len(matches),
            "consistent_rows": consistent_count,
            "warning_rows": warning_count,
            "deviation_rows": deviation_count,
            "unmatched_rows": len(unmatched_rows),
            "component_utxo_count": len(component_utxos),
        },
        "matches": matches,
        "deviations": deviation_rows,
        "unmatched": unmatched_rows,
        "component_utxos": component_utxos,
        "proofs": proofs,
        "review_trips": review_trips,
        "thresholds": {
            "warning_ratio": _round(warning_ratio, 6),
            "review_ratio": _round(review_ratio, 6),
            "threshold_spec_uri": _to_text(threshold_spec_uri).strip(),
        },
    }


def run_bidirectional_closure(
    *,
    sb: Any,
    body: dict[str, Any],
    commit: bool = False,
) -> dict[str, Any]:
    project_uri = _to_text(body.get("project_uri")).strip()
    node_uri = _to_text(body.get("node_uri")).strip()
    source = _to_text(body.get("change_source") or "design").strip().lower()
    if not project_uri or not node_uri:
        raise HTTPException(400, "project_uri and node_uri are required")
    owner_uri = _to_text(body.get("owner_uri")).strip() or f"{project_uri.rstrip('/')}/role/system/"
    delta_ratio = abs(_to_float(body.get("delta_ratio"), 0.0))
    matched_codes = [str(x).strip() for x in (body.get("matched_boq_codes") or []) if str(x).strip()]

    forward_actions: list[dict[str, Any]] = []
    reverse_actions: list[dict[str, Any]] = []
    if source == "design":
        forward_actions.append(
            {
                "action": "propose_boq_update",
                "reason": "design_changed",
                "node_uri": node_uri,
                "target_boq_codes": matched_codes,
                "delta_ratio": _round(delta_ratio, 6),
            }
        )
        reverse_actions.append(
            {
                "action": "open_trip_review",
                "reason": "design_to_boq_sync_required",
                "node_uri": node_uri,
            }
        )
    else:
        forward_actions.append(
            {
                "action": "propose_design_manifest_update",
                "reason": "boq_adjusted",
                "node_uri": node_uri,
                "target_boq_codes": matched_codes,
                "delta_ratio": _round(delta_ratio, 6),
            }
        )
        reverse_actions.append(
            {
                "action": "open_trip_review",
                "reason": "boq_to_design_sync_required",
                "node_uri": node_uri,
            }
        )

    proof_id = f"GP-SYNC-{_sha16(f'{project_uri}:{node_uri}:{source}:{datetime.now(UTC).isoformat()}').upper()}"
    state_data = {
        "proof_kind": "Design-BOQ Bidirectional Sync Proof",
        "change_source": source,
        "node_uri": node_uri,
        "delta_ratio": _round(delta_ratio, 6),
        "forward_actions": forward_actions,
        "reverse_actions": reverse_actions,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    proof = _create_proof(
        sb=sb,
        commit=bool(commit),
        proof_id=proof_id,
        owner_uri=owner_uri,
        project_uri=project_uri,
        result="OBSERVE",
        segment_uri=f"{project_uri.rstrip('/')}/design-boq/sync/{_sha16(node_uri)}",
        state_data=state_data,
    )

    return {
        "ok": True,
        "project_uri": project_uri,
        "node_uri": node_uri,
        "change_source": source,
        "forward_actions": forward_actions,
        "reverse_actions": reverse_actions,
        "proof": proof,
    }


__all__ = [
    "match_boq_with_design_manifest",
    "parse_design_manifest_from_upload",
    "run_bidirectional_closure",
]

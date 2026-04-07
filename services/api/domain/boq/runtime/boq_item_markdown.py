"""BOQItem markdown dossier generation and auto-refresh helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import os
import re
from typing import Any

from services.api.domain.projects.gitpeg_sdk import register_entity


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _safe_slug(value: Any) -> str:
    text = _to_text(value).strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff._-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "project"


def _norm_decimal_text(value: Any, default: str = "0") -> str:
    text = _to_text(value, default).strip() or default
    try:
        num = Decimal(text)
    except (InvalidOperation, ValueError):
        return default
    return format(num.normalize(), "f")


def _norm_decimal(value: Any, default: str = "0") -> Decimal:
    text = _norm_decimal_text(value, default)
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _decimal_or_none(value: Any) -> Decimal | None:
    text = _to_text(value).strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _format_amount(value: Any) -> str:
    num = _norm_decimal(value, "0")
    return f"{num:,.4f}".rstrip("0").rstrip(".")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _default_output_root() -> Path:
    env = _to_text(os.getenv("BOQ_ITEM_DOCS_DIR") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (_repo_root() / "docs" / "boq").resolve()


def _project_slug(project_uri: str) -> str:
    text = _to_text(project_uri).strip().rstrip("/")
    if not text:
        return "project"
    return _safe_slug(text.split("/")[-1])


def _normalize_boq_uri_from_segment(segment_uri: str) -> str:
    uri = _to_text(segment_uri).strip()
    if not uri.startswith("v://"):
        return ""
    token = "/spu-mapping/"
    if token in uri:
        return uri.split(token, 1)[0].rstrip("/")
    return uri.rstrip("/")


def _resolve_boq_uri(*, state_data: dict[str, Any], segment_uri: str = "") -> str:
    for key in (
        "boq_item_canonical_uri",
        "boq_item_v_uri",
        "boq_item_uri",
    ):
        text = _to_text(state_data.get(key)).strip()
        if text:
            return text.rstrip("/")
    ref = _as_dict(state_data.get("project_boq_item_ref"))
    text = _to_text(ref.get("boq_v_uri")).strip()
    if text:
        return text.rstrip("/")
    return _normalize_boq_uri_from_segment(segment_uri)


def _extract_item_id(boq_v_uri: str, state_data: dict[str, Any]) -> str:
    code = _to_text(state_data.get("item_no")).strip()
    if code:
        return code
    uri = _to_text(boq_v_uri).strip().rstrip("/")
    return uri.split("/")[-1] if uri else ""


def _proof_rows_for_boq(*, sb: Any, project_uri: str, boq_v_uri: str) -> list[dict[str, Any]]:
    if sb is None:
        return []
    rows: list[dict[str, Any]] = []
    try:
        res = (
            sb.table("proof_utxo")
            .select("proof_id,proof_hash,proof_type,result,spent,spend_tx_id,segment_uri,state_data,created_at")
            .eq("project_uri", project_uri)
            .like("segment_uri", f"{boq_v_uri}%")
            .order("created_at")
            .limit(1000)
            .execute()
        )
        rows = [row for row in (res.data or []) if isinstance(row, dict)]
    except Exception:
        rows = []
    return rows


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = _to_text(value).strip()
        if text:
            return text
    return ""


def _extract_gate_lines(state_data: dict[str, Any]) -> list[str]:
    snapshot = _as_dict(state_data.get("standard_spu_snapshot"))
    qc_gates = _as_list(snapshot.get("qc_gates"))
    lines: list[str] = []
    for gate in qc_gates:
        if not isinstance(gate, dict):
            continue
        metric = _to_text(gate.get("metric")).strip()
        operator = _to_text(gate.get("operator")).strip()
        threshold = gate.get("threshold")
        unit = _to_text(gate.get("unit")).strip()
        parts = [metric or "gate", operator or ""]
        if isinstance(threshold, list):
            parts.append(f"[{', '.join(_to_text(x) for x in threshold)}]")
        else:
            parts.append(_to_text(threshold))
        text = " ".join([p for p in parts if p]).strip()
        if unit:
            text = f"{text} {unit}".strip()
        if text:
            lines.append(text)
    if lines:
        return lines
    for key in ("linked_gate_ids", "ref_gate_uris"):
        for item in _as_list(state_data.get(key)):
            text = _to_text(item).strip()
            if text:
                lines.append(text)
    return lines


def _mapping_spu_uris(*, state_data: dict[str, Any], mapping_rows: list[dict[str, Any]]) -> list[str]:
    uris: list[str] = []
    primary = _to_text(state_data.get("ref_spu_uri")).strip()
    if primary:
        uris.append(primary)
    for row in mapping_rows:
        if not isinstance(row, dict):
            continue
        uri = _to_text(row.get("spu_uri")).strip()
        if uri:
            uris.append(uri)
    seen: set[str] = set()
    out: list[str] = []
    for uri in uris:
        norm = uri.rstrip("/")
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    return out


def _to_normref_uri(uri: str) -> str:
    text = _to_text(uri).strip().rstrip("/")
    if not text:
        return ""
    if text.startswith("v://normref.com/"):
        return text
    if text.startswith("v://norm/spu/"):
        return "v://normref.com/spu/" + text.split("/spu/", 1)[1]
    if text.startswith("v://norm/qc/"):
        return "v://normref.com/qc/" + text.split("/qc/", 1)[1]
    return text


def _infer_main_logic_uri(*, state_data: dict[str, Any], spu_uris: list[str], item_id: str, description: str) -> str:
    explicit = _to_text(state_data.get("ref_qc_protocol_uri")).strip()
    if explicit:
        return _to_normref_uri(explicit)
    raw_spu = _to_text(state_data.get("ref_spu_uri")).strip()
    name = f"{item_id} {description}".lower()
    if "raft" in name or "\u7b4f" in description:
        return "v://normref.com/qc/raft-foundation@v1"
    token = ""
    if raw_spu.startswith("v://"):
        token = raw_spu.rstrip("/").split("/")[-1]
    if not token and spu_uris:
        token = _to_text(spu_uris[0]).strip().rstrip("/").split("/")[-1]
    token = token or "generated"
    return f"v://normref.com/qc/{token}"
def _infer_aux_logic_uris(*, state_data: dict[str, Any], spu_uris: list[str], main_logic_uri: str) -> list[str]:
    explicit = [
        _to_normref_uri(_to_text(x).strip())
        for x in _as_list(state_data.get("aux_logic_uris"))
        if _to_text(x).strip()
    ]
    if explicit:
        return [x for x in explicit if x and x != main_logic_uri]
    out: list[str] = []
    for spu in spu_uris:
        mapped = _to_normref_uri(spu)
        if mapped and mapped != main_logic_uri and mapped not in out:
            out.append(mapped)
    return out


def _derive_logic_inputs(*, state_data: dict[str, Any], gate_lines: list[str], main_logic_uri: str) -> list[dict[str, str]]:
    explicit = _as_list(state_data.get("logic_inputs"))
    parsed_explicit: list[dict[str, str]] = []
    for item in explicit:
        if not isinstance(item, dict):
            continue
        name = _to_text(item.get("name")).strip()
        hint = _to_text(item.get("hint")).strip()
        unit = _to_text(item.get("unit")).strip()
        if not name:
            continue
        parsed_explicit.append({"name": name, "hint": hint, "unit": unit})
    if parsed_explicit:
        return parsed_explicit

    text = " ".join([_to_text(x).lower() for x in gate_lines]) + " " + _to_text(main_logic_uri).lower()
    out: list[dict[str, str]] = []

    def _append(name: str, hint: str, unit: str = "") -> None:
        if any(_to_text(i.get("name")).strip() == name for i in out):
            return
        out.append({"name": name, "hint": hint, "unit": unit})

    if "diameter" in text or "\u76f4\u5f84" in text:
        _append("design_diameter", "Design diameter from drawing", "mm")
        _append("measured_diameter", "Measured diameter from field", "mm")
    if "spacing" in text or "\u95f4\u8ddd" in text:
        _append("measured_spacing", "Measured spacing from field", "mm")
    if "\u4fdd\u62a4\u5c42" in text or "protection" in text:
        _append("measured_protection_layer", "Measured protection layer thickness", "mm")
    if "weld" in text or "\u710a" in text:
        _append("weld_quality_level", "Weld quality level (I/II/III)")
    if "raft" in text or "\u7b4f" in text:
        _append("design_thickness", "Design raft thickness from drawing", "mm")
        _append("measured_thickness", "Measured raft thickness from field", "mm")
        _append("measured_concrete_strength", "Measured concrete strength", "MPa")
        _append("measured_rebar_spacing", "Measured rebar spacing", "mm")
    if not out:
        _append("measured_value", "Measured value from field")
    return out
def _derive_state_matrix(*, state_data: dict[str, Any], proof_rows: list[dict[str, Any]]) -> dict[str, Any]:
    component_count = int(_norm_decimal(state_data.get("topology_component_count") or state_data.get("component_count"), "0"))
    forms_per_component = int(_norm_decimal(state_data.get("forms_per_component"), "2"))
    if forms_per_component <= 0:
        forms_per_component = 2
    expected_tables = int(_norm_decimal(state_data.get("expected_qc_table_count"), "0"))
    if expected_tables <= 0 and component_count > 0:
        expected_tables = component_count * forms_per_component

    generated = int(_norm_decimal(state_data.get("generated_qc_table_count"), "0"))
    signed_pass = int(_norm_decimal(state_data.get("signed_pass_table_count"), "0"))
    if generated <= 0:
        generated = sum(1 for row in proof_rows if _to_text(row.get("proof_type")).strip() == "inspection")
    if signed_pass <= 0:
        signed_pass = sum(
            1
            for row in proof_rows
            if _to_text(row.get("proof_type")).strip() == "inspection"
            and _to_text(row.get("result")).strip().upper() == "PASS"
        )

    pending = expected_tables - generated if expected_tables > 0 else 0
    if pending < 0:
        pending = 0
    return {
        "component_count": component_count,
        "forms_per_component": forms_per_component,
        "expected_qc_table_count": expected_tables,
        "generated_qc_table_count": generated,
        "signed_pass_table_count": signed_pass,
        "pending_qc_table_count": pending,
    }


def _topology_anchor_uri(*, boq_v_uri: str, bridge_uri: str, item_id: str) -> str:
    bridge = _to_text(bridge_uri).strip().rstrip("/")
    if not bridge.startswith("v://"):
        return _to_text(boq_v_uri).strip().rstrip("/")
    code = _to_text(item_id).strip() or _to_text(boq_v_uri).strip().rstrip("/").split("/")[-1]
    return f"{bridge}/boq/{code}"


def _derive_status(*, state_data: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    contract_qty = _norm_decimal(
        state_data.get("contract_quantity")
        if state_data.get("contract_quantity") is not None
        else state_data.get("utxo_quantity"),
        "0",
    )
    if not rows:
        initial_utxo_id = _to_text(_as_dict(state_data.get("genesis_proof")).get("proof_id")).strip()
        status = "UNSPENT" if contract_qty > 0 else "UNKNOWN"
        return {
            "initial_utxo_id": initial_utxo_id,
            "initial_qty": contract_qty,
            "remaining_qty": contract_qty,
            "consumed_qty": Decimal("0"),
            "status": status,
            "latest_proof_id": "",
            "latest_qc_proof_id": "",
        }

    initial_row = rows[0]
    initial_utxo_id = _to_text(initial_row.get("proof_id")).strip()
    initial_qty = contract_qty
    for row in rows:
        sd = _as_dict(row.get("state_data"))
        if _to_text(sd.get("utxo_kind")).strip() == "BOQ_INITIAL" and sd.get("utxo_quantity") is not None:
            initial_qty = _norm_decimal(sd.get("utxo_quantity"), _norm_decimal_text(contract_qty))
            initial_row = row
            initial_utxo_id = _to_text(row.get("proof_id")).strip()
            break
    remaining_qty = Decimal("0")
    for row in rows:
        if bool(row.get("spent")):
            continue
        sd = _as_dict(row.get("state_data"))
        qty = _decimal_or_none(sd.get("utxo_quantity"))
        if qty is None:
            continue
        remaining_qty += qty
    if remaining_qty <= Decimal("0") and not any(not bool(row.get("spent")) for row in rows):
        remaining_qty = Decimal("0")
    if remaining_qty > initial_qty and initial_qty > 0:
        remaining_qty = initial_qty
    consumed_qty = initial_qty - remaining_qty
    if consumed_qty < Decimal("0"):
        consumed_qty = Decimal("0")
    if remaining_qty <= Decimal("0"):
        status = "CONSUMED"
    elif remaining_qty < initial_qty:
        status = "PARTIALLY_CONSUMED"
    else:
        status = "UNSPENT"
    latest = rows[-1]
    latest_proof_id = _to_text(latest.get("proof_id")).strip()
    latest_qc_proof_id = ""
    for row in reversed(rows):
        if _to_text(row.get("proof_type")).strip() == "inspection":
            latest_qc_proof_id = _to_text(row.get("proof_id")).strip()
            break
    return {
        "initial_utxo_id": initial_utxo_id,
        "initial_qty": initial_qty,
        "remaining_qty": remaining_qty,
        "consumed_qty": consumed_qty,
        "status": status,
        "latest_proof_id": latest_proof_id,
        "latest_qc_proof_id": latest_qc_proof_id,
    }


def _event_label(row: dict[str, Any]) -> str:
    ptype = _to_text(row.get("proof_type")).strip()
    segment = _to_text(row.get("segment_uri")).strip()
    if "/spu-mapping/" in segment:
        return "SPU mapping updated"
    if ptype == "zero_ledger":
        return "scan initialized"
    if ptype == "inspection":
        return "quality inspection updated"
    if ptype == "payment":
        return "payment settlement updated"
    return f"{ptype or 'proof'} updated"


def _version_history(rows: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    if not rows:
        return lines
    idx = 0
    for row in rows:
        created_at = _to_text(row.get("created_at")).strip()
        label = _event_label(row)
        ver = f"v1.{idx}"
        idx += 1
        lines.append(f"- {ver}（{created_at or '-'}）：{label}")
    return lines


def _inline_list(values: list[Any]) -> str:
    cleaned = [_to_text(x).strip() for x in values if _to_text(x).strip()]
    if not cleaned:
        return "[]"
    return "[" + ", ".join(f"\"{item.replace('\"', '\\\"')}\"" for item in cleaned) + "]"


def _inline_dict(data: dict[str, Any]) -> str:
    if not data:
        return "{}"
    pairs: list[str] = []
    for key, value in data.items():
        k = _to_text(key).strip()
        v = _to_text(value).strip()
        if not k:
            continue
        pairs.append(f"\"{k}\": \"{v}\"")
    return "{" + ", ".join(pairs) + "}"


def _derive_required_trip_roles(state_data: dict[str, Any]) -> list[str]:
    explicit = [_to_text(x).strip() for x in _as_list(state_data.get("required_trip_roles")) if _to_text(x).strip()]
    if explicit:
        return explicit
    return ["inspector.quality.check", "supervisor.approve"]


def _derive_dtorole_permissions(state_data: dict[str, Any]) -> dict[str, str]:
    explicit = state_data.get("dtorole_permissions")
    if isinstance(explicit, dict):
        mapped = {_to_text(k).strip(): _to_text(v).strip() for k, v in explicit.items() if _to_text(k).strip()}
        if mapped:
            return mapped
    if isinstance(explicit, list):
        mapped: dict[str, str] = {}
        for item in explicit:
            if not isinstance(item, dict):
                continue
            role = _to_text(item.get("role")).strip()
            action = _to_text(item.get("permission") or item.get("action")).strip()
            if role and action:
                mapped[role] = action
        if mapped:
            return mapped
    return {
        "EXECUTOR": "can_fill_measured",
        "SUPERVISOR": "can_approve",
        "OWNER": "can_view_full_proof",
    }


def _derive_pre_conditions(state_data: dict[str, Any]) -> list[str]:
    explicit = [_to_text(x).strip() for x in _as_list(state_data.get("pre_conditions")) if _to_text(x).strip()]
    if explicit:
        return explicit
    return ["原材料复检合格", "设备校准有效"]


def _derive_relations(*, state_data: dict[str, Any], component_count: int) -> dict[str, list[str]]:
    materials = [_to_text(x).strip() for x in _as_list(state_data.get("material_uris") or state_data.get("related_material_uris")) if _to_text(x).strip()]
    drawings = [_to_text(x).strip() for x in _as_list(state_data.get("drawing_uris") or state_data.get("ref_drawing_uris")) if _to_text(x).strip()]
    components = [_to_text(x).strip() for x in _as_list(state_data.get("component_uris") or state_data.get("related_component_uris")) if _to_text(x).strip()]
    if not components and component_count > 0:
        components = [f"v://component/derived/{component_count}"]
    return {
        "materials": materials,
        "drawings": drawings,
        "components": components,
    }


def _derive_test_data(state_data: dict[str, Any]) -> list[Any]:
    candidate = state_data.get("test_data")
    if isinstance(candidate, list):
        return candidate
    if isinstance(candidate, dict):
        return [candidate]
    measured = state_data.get("measured_values")
    if isinstance(measured, list):
        return measured
    if isinstance(measured, dict):
        return [measured]
    return []


def _render_markdown(context: dict[str, Any]) -> str:
    title = _to_text(context.get("title")).strip()
    boq_v_uri = _to_text(context.get("boq_v_uri")).strip()
    topology_uri = _to_text(context.get("topology_uri")).strip() or boq_v_uri
    project_uri = _to_text(context.get("project_uri")).strip()
    bridge_uri = _to_text(context.get("bridge_uri")).strip()
    item_id = _to_text(context.get("item_id")).strip()
    description = _to_text(context.get("description")).strip()
    division = _to_text(context.get("division")).strip()
    unit = _to_text(context.get("unit")).strip()
    quantity = _to_text(context.get("quantity")).strip()
    unit_price = _to_text(context.get("unit_price")).strip()
    total_amount = _to_text(context.get("total_amount")).strip()
    doc_uri = _to_text(context.get("doc_uri")).strip()

    doc_type = _to_text(context.get("doc_type")).strip()
    doc_id = _to_text(context.get("doc_id")).strip()
    doc_version = _to_text(context.get("doc_version")).strip()
    created_at = _to_text(context.get("created_at")).strip()
    jurisdiction = _to_text(context.get("jurisdiction")).strip()
    trip_role = _to_text(context.get("trip_role")).strip()
    dtorole_context = _to_text(context.get("dtorole_context")).strip()

    required_trip_roles = _as_list(context.get("required_trip_roles"))
    dtorole_permissions = _as_dict(context.get("dtorole_permissions"))
    pre_conditions = _as_list(context.get("pre_conditions"))

    norm_refs = [_to_text(x).strip() for x in _as_list(context.get("norm_refs")) if _to_text(x).strip()]
    gate_lines = [_to_text(x).strip() for x in _as_list(context.get("gate_lines")) if _to_text(x).strip()]
    meter_rules = [_to_text(x).strip() for x in _as_list(context.get("meter_rules")) if _to_text(x).strip()]

    main_logic_uri = _to_text(context.get("main_logic_uri")).strip()
    aux_logic_uris = [_to_text(x).strip() for x in _as_list(context.get("aux_logic_uris")) if _to_text(x).strip()]
    logic_inputs = [x for x in _as_list(context.get("logic_inputs")) if isinstance(x, dict)]
    relations = _as_dict(context.get("relations"))
    test_data = _as_list(context.get("test_data"))
    trip_context = _as_dict(context.get("trip_context"))

    initial_utxo = _to_text(context.get("initial_utxo_id")).strip()
    consumed = _to_text(context.get("consumed_qty")).strip()
    remaining = _to_text(context.get("remaining_qty")).strip()
    status = _to_text(context.get("status")).strip()
    scan_proof = _to_text(context.get("scan_proof")).strip()
    mapping_proofs = [f"`{_to_text(x).strip()}`" for x in _as_list(context.get("mapping_proofs")) if _to_text(x).strip()]
    latest_qc_proof = _to_text(context.get("latest_qc_proof")).strip()
    latest_proof = _to_text(context.get("latest_proof")).strip()
    version_lines = _as_list(context.get("version_lines"))
    updated_at = _to_text(context.get("updated_at")).strip()
    actor_uri = _to_text(context.get("actor_uri")).strip()
    state_matrix = _as_dict(context.get("state_matrix"))
    lifecycle_stage = _to_text(context.get("lifecycle_stage")).strip()
    current_trip_role = _to_text(context.get("current_trip_role")).strip()
    dtorole_state = _as_dict(context.get("dtorole_state"))
    next_action = _to_text(context.get("next_action")).strip()
    proof_hashes = [_to_text(x).strip() for x in _as_list(context.get("proof_hashes")) if _to_text(x).strip()]
    trip_proof_hashes = [_to_text(x).strip() for x in _as_list(context.get("trip_proof_hashes")) if _to_text(x).strip()]
    data_hash = _to_text(context.get("data_hash")).strip()
    witness_logs = [_to_text(x).strip() for x in _as_list(context.get("witness_logs")) if _to_text(x).strip()]
    audit_trail = [_to_text(x).strip() for x in _as_list(context.get("audit_trail")) if _to_text(x).strip()]

    lines: list[str] = [f"# {title}", ""]
    lines.append("**Layer 1: Header（身份层）**")
    lines.append(f"- doc_type: {doc_type or '-'}")
    lines.append(f"- doc_id: {doc_id or '-'}")
    lines.append(f"- v_uri: {topology_uri or '-'}")
    lines.append(f"- canonical_v_uri: {boq_v_uri or '-'}")
    lines.append(f"- version: {doc_version or '-'}")
    lines.append(f"- created_at: {created_at or '-'}")
    lines.append(f"- project_ref: {project_uri or '-'}")
    lines.append(f"- bridge_ref: {bridge_uri or '-'}")
    lines.append(f"- jurisdiction: {jurisdiction or '-'}")
    lines.append(f"- trip_role: {trip_role or 'null'}")
    lines.append(f"- dtorole_context: {dtorole_context or 'null'}")
    if doc_uri:
        lines.append(f"- doc_uri: {doc_uri}")

    lines.extend(["", "**Layer 2: Gate（门槛层）**"])
    lines.append(f"- required_trip_roles: {_inline_list(required_trip_roles)}")
    lines.append("- dtorole_permissions:")
    if dtorole_permissions:
        for role, permission in dtorole_permissions.items():
            lines.append(f"  - {role}: {permission}")
    else:
        lines.append("  - -")
    lines.append(f"- pre_conditions: {_inline_list(pre_conditions)}")
    lines.append(f"- norm_refs: {_inline_list(norm_refs)}")
    lines.append(f"- normref_main_logic: `{main_logic_uri or '-'}`")
    lines.append(f"- normref_aux_logic: {_inline_list(aux_logic_uris)}")
    lines.append("- gate_rules:")
    if gate_lines:
        for item in gate_lines:
            lines.append(f"  - {item}")
    else:
        lines.append("  - -")
    lines.append(f"- meter_rules: {_inline_list(meter_rules)}")
    lines.append("- logic_inputs:")
    if logic_inputs:
        for item in logic_inputs:
            name = _to_text(item.get("name")).strip()
            hint = _to_text(item.get("hint")).strip()
            unit_text = _to_text(item.get("unit")).strip()
            tail = f"，单位 {unit_text}" if unit_text else ""
            lines.append(f"  - {name}: {hint}{tail}")
    else:
        lines.append("  - measured_value: 现场输入")

    lines.extend(["", "**Layer 3: Body（内容层）**"])
    lines.append("- basic:")
    lines.append(f"  - description: \"{description or '-'}\"")
    lines.append(f"  - boq_item_id: \"{item_id or '-'}\"")
    lines.append(f"  - division: \"{division or '-'}\"")
    lines.append(f"  - unit: \"{unit or '-'}\"")
    lines.append(f"  - boq_quantity: {quantity or '0'}")
    lines.append(f"  - unit_price: {unit_price or '0'}")
    lines.append(f"  - total_amount: {total_amount or '0'}")
    lines.append(f"- test_data: {_inline_list(test_data)}")
    lines.append(f"- relations: {_inline_dict({'materials': _inline_list(_as_list(relations.get('materials'))), 'drawings': _inline_list(_as_list(relations.get('drawings'))), 'components': _inline_list(_as_list(relations.get('components')))} )}")
    lines.append(f"- trip_context: {_inline_dict(trip_context)}")

    lines.extend(["", "**Layer 4: Proof（证明层）**"])
    lines.append(f"- trip_proof_hash: {_inline_list(trip_proof_hashes)}")
    lines.append(f"- proof_hashes: {_inline_list(proof_hashes)}")
    lines.append(f"- data_hash: \"{data_hash or '-'}\"")
    lines.append(f"- witness_logs: {_inline_list(witness_logs)}")
    lines.append(f"- audit_trail: {_inline_list(audit_trail)}")
    lines.append(f"- scan_proof: `{scan_proof or '-'}`")
    if mapping_proofs:
        lines.append(f"- mapping_proof: {', '.join(mapping_proofs)}")
    else:
        lines.append("- mapping_proof: `-`")
    lines.append(f"- latest_qc_proof: `{latest_qc_proof or '-'}`")
    lines.append(f"- latest_proof: `{latest_proof or '-'}`")

    lines.extend(["", "**Layer 5: State（状态层）**"])
    lines.append(f"- lifecycle_stage: \"{lifecycle_stage or 'draft'}\"")
    lines.append(f"- current_trip_role: \"{current_trip_role or 'null'}\"")
    lines.append("- state_matrix:")
    lines.append(f"  - total_qc_tables: {_to_text(state_matrix.get('expected_qc_table_count') or '0')}")
    lines.append(f"  - generated: {_to_text(state_matrix.get('generated_qc_table_count') or '0')}")
    lines.append(f"  - signed: {_to_text(state_matrix.get('signed_pass_table_count') or '0')}")
    lines.append(f"  - pending: {_to_text(state_matrix.get('pending_qc_table_count') or '0')}")
    lines.append("- execution_state:")
    lines.append(f"  - initial_utxo: `{initial_utxo or '-'}`")
    lines.append(f"  - 已消耗数量：{consumed or '0'} {unit}".rstrip())
    lines.append(f"  - 剩余数量：{remaining or '0'} {unit}".rstrip())
    lines.append(f"  - 当前状态：`{status or '-'}`")
    lines.append(f"- dtorole_state: {_inline_dict(dtorole_state)}")
    lines.append(f"- next_action: \"{next_action or '-'}\"")

    lines.extend(["", "**版本历史与回溯**"])
    lines.extend(version_lines or ["- v1.0 (-)：初始生成"])
    lines.extend(["", "**最后更新**", f"{updated_at or '-'}"])
    lines.append(f"生成者：{actor_uri or '-'}")
    return "\n".join(lines).rstrip() + "\n"
def _register_markdown_doc_uri(
    *,
    sb: Any,
    boq_v_uri: str,
    relative_path: str,
    commit: bool,
) -> str:
    if not boq_v_uri.startswith("v://"):
        return ""
    try:
        out = register_entity(
            sb=sb,
            entity_type="docs",
            parent_uri=boq_v_uri,
            identifier="boq-item.md",
            metadata={"file_path": relative_path, "doc_type": "boq-item-markdown"},
            commit=bool(commit and sb is not None),
        )
        return _to_text(out.get("uri")).strip()
    except Exception:
        return ""


def sync_boq_item_markdown(
    *,
    sb: Any,
    project_uri: str,
    boq_v_uri: str,
    state_data: dict[str, Any] | None = None,
    mapping_rows: list[dict[str, Any]] | None = None,
    actor_uri: str = "",
    reason: str = "",
    write_file: bool = True,
    output_root: Path | str | None = None,
    register_doc: bool = True,
) -> dict[str, Any]:
    project = _to_text(project_uri).strip().rstrip("/")
    boq_uri = _to_text(boq_v_uri).strip().rstrip("/")
    if not project or not boq_uri:
        return {"ok": False, "error": "project_uri_and_boq_v_uri_required"}
    sd = _as_dict(state_data)
    proof_rows = _proof_rows_for_boq(sb=sb, project_uri=project, boq_v_uri=boq_uri)
    latest_sd = dict(sd)
    if proof_rows:
        candidate = _as_dict(proof_rows[-1].get("state_data"))
        if candidate:
            latest_sd = {**latest_sd, **candidate}
    item_id = _extract_item_id(boq_uri, latest_sd)
    desc = _first_non_empty(latest_sd.get("item_name"), latest_sd.get("description"), item_id)
    unit = _first_non_empty(latest_sd.get("unit"), _as_dict(latest_sd.get("boq_item")).get("unit"))
    quantity = _first_non_empty(
        latest_sd.get("contract_quantity"),
        latest_sd.get("utxo_quantity"),
        _as_dict(latest_sd.get("project_boq_item_ref")).get("quantity"),
    )
    unit_price = _first_non_empty(latest_sd.get("contract_unit_price"), latest_sd.get("unit_price"), "0")
    total_amount = _first_non_empty(latest_sd.get("contract_total"), "0")
    bridge_uri = _first_non_empty(latest_sd.get("bridge_uri"), _as_dict(latest_sd.get("project_boq_item_ref")).get("bridge_uri"))
    norm_refs = list(_as_list(latest_sd.get("norm_refs")))
    ref_spec_uri = _to_text(latest_sd.get("ref_spec_uri")).strip()
    if ref_spec_uri and ref_spec_uri not in norm_refs:
        norm_refs.append(ref_spec_uri)
    meter_rules = []
    ref_meter_rule_uri = _to_text(latest_sd.get("ref_meter_rule_uri")).strip()
    if ref_meter_rule_uri:
        meter_rules.append(ref_meter_rule_uri)
    spu_refs = _mapping_spu_uris(state_data=latest_sd, mapping_rows=mapping_rows or [])
    gate_lines = _extract_gate_lines(latest_sd)
    main_logic_uri = _infer_main_logic_uri(
        state_data=latest_sd,
        spu_uris=spu_refs,
        item_id=item_id,
        description=desc,
    )
    aux_logic_uris = _infer_aux_logic_uris(state_data=latest_sd, spu_uris=spu_refs, main_logic_uri=main_logic_uri)
    logic_inputs = _derive_logic_inputs(
        state_data=latest_sd,
        gate_lines=gate_lines,
        main_logic_uri=main_logic_uri,
    )
    state_matrix = _derive_state_matrix(state_data=latest_sd, proof_rows=proof_rows)
    topology_uri = _topology_anchor_uri(boq_v_uri=boq_uri, bridge_uri=bridge_uri, item_id=item_id)
    status_payload = _derive_status(state_data=latest_sd, rows=proof_rows)
    mapping_proof_ids: list[str] = []
    for row in proof_rows:
        segment = _to_text(row.get("segment_uri")).strip()
        if "/spu-mapping/" in segment:
            pid = _to_text(row.get("proof_id")).strip()
            if pid and pid not in mapping_proof_ids:
                mapping_proof_ids.append(pid)
    proof_hashes: list[str] = []
    trip_proof_hashes: list[str] = []
    for row in proof_rows:
        proof_hash = _to_text(row.get("proof_hash")).strip()
        if proof_hash and proof_hash not in proof_hashes:
            proof_hashes.append(proof_hash)
        ptype = _to_text(row.get("proof_type")).strip()
        if ptype in {"inspection", "payment"} and proof_hash and proof_hash not in trip_proof_hashes:
            trip_proof_hashes.append(proof_hash)
    scan_proof_id = _to_text(_as_dict(latest_sd.get("genesis_proof")).get("proof_id")).strip()
    if not scan_proof_id and proof_rows:
        for row in proof_rows:
            if _to_text(row.get("proof_type")).strip() == "zero_ledger":
                scan_proof_id = _to_text(row.get("proof_id")).strip()
                break
    created_at = _to_text(latest_sd.get("created_at")).strip()
    if not created_at and proof_rows:
        created_at = _to_text(proof_rows[0].get("created_at")).strip()
    if not created_at:
        created_at = datetime.now(UTC).isoformat(timespec="seconds")
    doc_type = _to_text(latest_sd.get("doc_type")).strip() or "v://normref.com/doc-type/boq-item@v1"
    doc_id = _to_text(latest_sd.get("doc_id")).strip() or f"BOQ-{item_id}-001"
    doc_version = _to_text(latest_sd.get("doc_version")).strip() or "v2.1"
    jurisdiction = _to_text(latest_sd.get("jurisdiction")).strip() or (" + ".join(norm_refs) if norm_refs else "")
    trip_role = _to_text(latest_sd.get("trip_role")).strip() or _to_text(reason).strip()
    dtorole_context = _to_text(latest_sd.get("dtorole_context")).strip()
    required_trip_roles = _derive_required_trip_roles(latest_sd)
    dtorole_permissions = _derive_dtorole_permissions(latest_sd)
    pre_conditions = _derive_pre_conditions(latest_sd)
    relations = _derive_relations(
        state_data=latest_sd,
        component_count=int(_norm_decimal(state_matrix.get("component_count"), "0")),
    )
    test_data = _derive_test_data(latest_sd)
    trip_context = _as_dict(latest_sd.get("trip_context"))
    if not trip_context:
        trip_context = {
            "executed_by": _to_text(latest_sd.get("executed_by")).strip(),
            "executed_at": _to_text(latest_sd.get("executed_at")).strip(),
        }
        trip_context = {k: v for k, v in trip_context.items() if v}
    lifecycle_stage = _to_text(latest_sd.get("lifecycle_stage")).strip().lower()
    if lifecycle_stage == "initial":
        lifecycle_stage = "draft"
    current_trip_role = _to_text(latest_sd.get("current_trip_role")).strip() or trip_role
    dtorole_state = _as_dict(latest_sd.get("dtorole_state"))
    if not dtorole_state:
        dtorole_state = {
            "SUPERVISOR": "pending_review",
            "PUBLIC": "summary_only",
        }
    next_action = _to_text(latest_sd.get("next_action")).strip()
    if not next_action:
        pending_count = int(_norm_decimal(state_matrix.get("pending_qc_table_count"), "0"))
        next_action = "等待现场测量员填写实测数据" if pending_count > 0 else "等待监理签认"
    data_hash = _to_text(latest_sd.get("data_hash")).strip() or _to_text(latest_sd.get("genesis_hash")).strip()
    witness_logs = _as_list(latest_sd.get("witness_logs"))
    audit_trail = _as_list(latest_sd.get("audit_trail"))

    output = Path(output_root).expanduser().resolve() if output_root else _default_output_root()
    project_folder = output / _project_slug(project)
    project_folder.mkdir(parents=True, exist_ok=True)
    md_path = project_folder / f"{_safe_slug(item_id)}.md"
    relative_path = str(md_path.relative_to(_repo_root())).replace("\\", "/") if _repo_root() in md_path.parents else str(md_path)
    doc_uri = _register_markdown_doc_uri(
        sb=sb,
        boq_v_uri=boq_uri,
        relative_path=relative_path,
        commit=bool(register_doc and write_file),
    ) if register_doc else ""
    context = {
        "title": f"BOQ-{item_id} {desc}".strip(),
        "doc_type": doc_type,
        "doc_id": doc_id,
        "doc_version": doc_version,
        "created_at": created_at,
        "boq_v_uri": boq_uri,
        "topology_uri": topology_uri,
        "doc_uri": doc_uri,
        "project_uri": project,
        "bridge_uri": bridge_uri,
        "jurisdiction": jurisdiction,
        "trip_role": trip_role,
        "dtorole_context": dtorole_context,
        "required_trip_roles": required_trip_roles,
        "dtorole_permissions": dtorole_permissions,
        "pre_conditions": pre_conditions,
        "item_id": item_id,
        "description": desc,
        "division": _first_non_empty(latest_sd.get("division"), _to_text(latest_sd.get("hierarchy_raw")).strip()),
        "unit": unit,
        "quantity": _norm_decimal_text(quantity, "0"),
        "unit_price": _format_amount(unit_price),
        "total_amount": _format_amount(total_amount),
        "spu_uris": spu_refs,
        "main_logic_uri": main_logic_uri,
        "aux_logic_uris": aux_logic_uris,
        "logic_inputs": logic_inputs,
        "norm_refs": norm_refs,
        "gate_lines": gate_lines,
        "meter_rules": meter_rules,
        "relations": relations,
        "test_data": test_data,
        "trip_context": trip_context,
        "state_matrix": state_matrix,
        "initial_utxo_id": status_payload.get("initial_utxo_id"),
        "consumed_qty": _norm_decimal_text(status_payload.get("consumed_qty"), "0"),
        "remaining_qty": _norm_decimal_text(status_payload.get("remaining_qty"), "0"),
        "status": status_payload.get("status"),
        "scan_proof": scan_proof_id,
        "mapping_proofs": mapping_proof_ids,
        "latest_qc_proof": status_payload.get("latest_qc_proof_id"),
        "latest_proof": status_payload.get("latest_proof_id"),
        "proof_hashes": proof_hashes,
        "trip_proof_hashes": trip_proof_hashes,
        "data_hash": data_hash,
        "witness_logs": witness_logs,
        "audit_trail": audit_trail,
        "lifecycle_stage": lifecycle_stage,
        "current_trip_role": current_trip_role,
        "dtorole_state": dtorole_state,
        "next_action": next_action,
        "version_lines": _version_history(proof_rows),
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "actor_uri": actor_uri,
        "reason": reason,
    }
    content = _render_markdown(context)
    wrote = False
    if write_file:
        md_path.write_text(content, encoding="utf-8")
        wrote = True
    return {
        "ok": True,
        "boq_v_uri": boq_uri,
        "item_id": item_id,
        "path": str(md_path),
        "relative_path": relative_path,
        "doc_uri": doc_uri,
        "wrote": wrote,
    }


def sync_boq_item_markdowns_from_chain(
    *,
    sb: Any,
    project_uri: str,
    preview_rows: list[dict[str, Any]],
    mapping_rows: list[dict[str, Any]],
    actor_uri: str = "",
    reason: str = "scan",
    write_file: bool = True,
    output_root: Path | str | None = None,
) -> dict[str, Any]:
    mapping_by_boq: dict[str, list[dict[str, Any]]] = {}
    for row in mapping_rows:
        if not isinstance(row, dict):
            continue
        boq_v_uri = _to_text(row.get("boq_v_uri")).strip().rstrip("/")
        if boq_v_uri:
            mapping_by_boq.setdefault(boq_v_uri, []).append(row)
    results: list[dict[str, Any]] = []
    for row in preview_rows:
        sd = _as_dict(row.get("state_data"))
        if not bool(sd.get("is_leaf")):
            continue
        boq_v_uri = _resolve_boq_uri(state_data=sd, segment_uri=_to_text(row.get("segment_uri")).strip())
        if not boq_v_uri:
            continue
        results.append(
            sync_boq_item_markdown(
                sb=sb,
                project_uri=project_uri,
                boq_v_uri=boq_v_uri,
                state_data=sd,
                mapping_rows=mapping_by_boq.get(boq_v_uri, []),
                actor_uri=actor_uri,
                reason=reason,
                write_file=bool(write_file),
                output_root=output_root,
                register_doc=True,
            )
        )
    return {
        "ok": True,
        "count": len(results),
        "items": results,
    }


def sync_boq_item_markdowns_for_uris(
    *,
    sb: Any,
    project_uri: str,
    boq_v_uris: list[str],
    actor_uri: str = "",
    reason: str = "consume",
    write_file: bool = True,
    output_root: Path | str | None = None,
) -> dict[str, Any]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in boq_v_uris:
        uri = _to_text(item).strip().rstrip("/")
        if not uri or uri in seen:
            continue
        seen.add(uri)
        deduped.append(uri)
    results: list[dict[str, Any]] = []
    for boq_uri in deduped:
        results.append(
            sync_boq_item_markdown(
                sb=sb,
                project_uri=project_uri,
                boq_v_uri=boq_uri,
                actor_uri=actor_uri,
                reason=reason,
                write_file=bool(write_file),
                output_root=output_root,
                register_doc=True,
            )
        )
    return {"ok": True, "count": len(results), "items": results}


__all__ = [
    "sync_boq_item_markdown",
    "sync_boq_item_markdowns_for_uris",
    "sync_boq_item_markdowns_from_chain",
]




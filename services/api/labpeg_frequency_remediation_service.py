from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import math
import re
from typing import Any

from fastapi import HTTPException

from services.api.proof_utxo_engine import ProofUTXOEngine


FREQUENCY_RULES = [
    {"prefix": "403-1-2", "group_qty": 60.0, "basis": "JTG F80 / JTG E60"},
    {"prefix": "403", "group_qty": 100.0, "basis": "JTG F80 chapter"},
    {"prefix": "400", "group_qty": 200.0, "basis": "QCSpec default"},
]


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        m = re.search(r"[-+]?\d+(?:\.\d+)?", _to_text(value))
        return float(m.group(0)) if m else None


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _stage(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    st = _to_text(sd.get("lifecycle_stage") or sd.get("status")).upper()
    if st:
        return st
    return "INITIAL" if _to_text(row.get("proof_type")).lower() == "zero_ledger" else ""


def _boq_uri(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    for key in ("boq_item_uri", "item_uri", "boq_uri"):
        val = _to_text(sd.get(key)).strip()
        if val.startswith("v://"):
            return val
    segment = _to_text(row.get("segment_uri")).strip()
    return segment if "/boq/" in segment else ""


def _item_no(boq_item_uri: str) -> str:
    return _to_text(boq_item_uri).rstrip("/").split("/")[-1]


def _parse_day(text: Any) -> date | None:
    raw = _to_text(text).strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except Exception:
        return None


def _find_project_by_uri(sb: Any, project_uri: str) -> dict[str, Any]:
    rows = (
        sb.table("projects")
        .select("id,v_uri,name,zero_equipment")
        .eq("v_uri", project_uri)
        .limit(1)
        .execute()
        .data
        or []
    )
    return _as_dict(rows[0]) if rows else {}


def _resolve_rule(item_no: str) -> dict[str, Any]:
    for rule in FREQUENCY_RULES:
        prefix = _to_text(rule["prefix"])
        if item_no == prefix or item_no.startswith(f"{prefix}-"):
            return rule
    return FREQUENCY_RULES[-1]


def _resolve_instrument_validity(project_row: dict[str, Any], instrument_sn: str, tested_at: str) -> dict[str, Any]:
    sn = _to_text(instrument_sn).strip()
    if not sn:
        return {"ok": False, "reason": "instrument_sn_required"}
    test_day = _parse_day(tested_at) or datetime.now(timezone.utc).date()
    equipment = _as_list(project_row.get("zero_equipment"))
    matched = None
    for row in equipment:
        d = _as_dict(row)
        joined = " ".join(
            [
                _to_text(d.get("model_no")).lower(),
                _to_text(d.get("toolpeg_uri")).lower(),
                _to_text(d.get("name")).lower(),
            ]
        )
        if sn.lower() in joined:
            matched = d
            break
    if matched is None:
        return {"ok": False, "reason": "instrument_not_registered"}
    valid_until = _parse_day(matched.get("valid_until"))
    if valid_until is None:
        return {"ok": False, "reason": "instrument_valid_until_missing", "matched": matched}
    remaining = (valid_until - test_day).days
    if remaining < 0:
        return {"ok": False, "reason": "instrument_calibration_expired", "matched": matched, "remaining_days": remaining}
    return {"ok": True, "reason": "ok", "matched": matched, "remaining_days": remaining, "valid_until": valid_until.isoformat()}


def resolve_dual_pass_gate(*, sb: Any, project_uri: str, boq_item_uri: str, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if rows is None:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("project_uri", project_uri)
            .order("created_at", desc=False)
            .limit(20000)
            .execute()
            .data
            or []
        )
    bucket = [x for x in rows if isinstance(x, dict) and _boq_uri(x) == boq_item_uri]
    qc_pass = [x for x in bucket if _to_text(x.get("proof_type")).lower() == "inspection" and _to_text(x.get("result")).upper() == "PASS" and _stage(x) == "ENTRY"]
    lab_pass = [x for x in bucket if _to_text(x.get("proof_type")).lower() == "lab" and _to_text(x.get("result")).upper() == "PASS"]
    return {
        "ok": bool(qc_pass) and bool(lab_pass),
        "qc_pass_count": len(qc_pass),
        "lab_pass_count": len(lab_pass),
        "latest_lab_pass_proof_id": _to_text((lab_pass[-1] if lab_pass else {}).get("proof_id")).strip(),
    }


def record_lab_test(*, sb: Any, project_uri: str, boq_item_uri: str, sample_id: str, jtg_form_code: str = "JTG-E60", instrument_sn: str = "", tested_at: str = "", witness_record: dict[str, Any] | None = None, sample_tracking: dict[str, Any] | None = None, metrics: list[dict[str, Any]] | None = None, result: str = "", executor_uri: str = "v://executor/lab/system/", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if not project_uri or not boq_item_uri:
        raise HTTPException(400, "project_uri and boq_item_uri are required")
    tested = tested_at or _utc_iso()
    project_row = _find_project_by_uri(sb, project_uri)
    validity = _resolve_instrument_validity(project_row, instrument_sn, tested)
    if not validity.get("ok"):
        raise HTTPException(409, f"instrument validation failed: {validity.get('reason')}")
    metric_rows = [x for x in _as_list(metrics) if isinstance(x, dict)]
    explicit = _to_text(result).upper().strip()
    lab_result = explicit if explicit in {"PASS", "FAIL", "OBSERVE", "PENDING"} else ("FAIL" if any(_to_text(_as_dict(x).get("result")).upper() == "FAIL" for x in metric_rows) else "PASS")
    sample = sample_id or f"SMP-{hashlib.sha256(boq_item_uri.encode('utf-8')).hexdigest()[:8].upper()}"
    payload = {
        "sample_id": sample,
        "boq_item_uri": boq_item_uri,
        "jtg_form_code": jtg_form_code or "JTG-E60",
        "tested_at": tested,
        "instrument_sn": instrument_sn,
        "instrument_validity": validity,
        "witness_record": _as_dict(witness_record),
        "sample_tracking": _as_dict(sample_tracking),
        "metrics": metric_rows,
        "metadata": _as_dict(metadata),
    }
    docpeg_push = {"ok": True, "target": "DocPeg.lab_report", "payload_hash": _sha(payload), "artifact_uri": f"{project_uri.rstrip('/')}/lab/{sample}/{_sha({'boq': boq_item_uri, 'ts': tested})[:12]}"}
    row = ProofUTXOEngine(sb).create(
        proof_id=f"GP-LAB-{_sha(payload)[:16].upper()}",
        owner_uri=executor_uri or "v://executor/lab/system/",
        project_uri=project_uri,
        project_id=project_row.get("id"),
        proof_type="lab",
        result=lab_result,
        state_data={
            "lifecycle_stage": "LAB_TEST",
            "status": "LAB_TEST",
            **payload,
            "docpeg_push": docpeg_push,
        },
        conditions=[],
        parent_proof_id=None,
        norm_uri=f"v://norm/{jtg_form_code or 'JTG-E60'}#lab_test",
        segment_uri=boq_item_uri,
        signer_uri=executor_uri or "v://executor/lab/system/",
        signer_role="LAB",
    )
    return {"ok": True, "proof_id": _to_text(row.get("proof_id")).strip(), "proof_hash": _to_text(row.get("proof_hash")).strip(), "result": lab_result, "instrument_validity": validity, "docpeg_push": docpeg_push}


def calc_inspection_frequency(*, sb: Any, boq_item_uri: str, project_uri: str = "") -> dict[str, Any]:
    uri = boq_item_uri.strip()
    if not uri:
        raise HTTPException(400, "boq_item_uri is required")
    p_uri = project_uri.strip() or (uri.split("/boq/", 1)[0] if "/boq/" in uri else "")
    if not p_uri:
        raise HTTPException(400, "project_uri is required")
    rows = (
        sb.table("proof_utxo")
        .select("*")
        .eq("project_uri", p_uri)
        .order("created_at", desc=False)
        .limit(20000)
        .execute()
        .data
        or []
    )
    bucket = [x for x in rows if isinstance(x, dict) and _boq_uri(x) == uri]
    if not bucket:
        raise HTTPException(404, "boq item not found")
    genesis = next((x for x in bucket if _stage(x) == "INITIAL" or _to_text(x.get("proof_type")).lower() == "zero_ledger"), bucket[0])
    design_qty = _to_float(_as_dict(genesis.get("state_data")).get("design_quantity")) or _to_float(_as_dict(_as_dict(genesis.get("state_data")).get("ledger")).get("initial_balance")) or 0.0
    item_no = _to_text(_as_dict(genesis.get("state_data")).get("item_no")).strip() or _item_no(uri)
    rule = _resolve_rule(item_no)
    expected = int(math.ceil(max(float(design_qty), 0.0) / max(float(rule["group_qty"]), 1.0))) if float(design_qty) > 0 else 0
    qc_rows = [x for x in bucket if _to_text(x.get("proof_type")).lower() == "inspection" and _stage(x) == "ENTRY"]
    qc_pass = [x for x in qc_rows if _to_text(x.get("result")).upper() == "PASS"]
    lab_rows = [x for x in bucket if _to_text(x.get("proof_type")).lower() == "lab"]
    lab_pass = [x for x in lab_rows if _to_text(x.get("result")).upper() == "PASS"]
    dual_done = min(len(qc_pass), len(lab_pass))
    missing = max(expected - dual_done, 0)
    return {
        "ok": True,
        "project_uri": p_uri,
        "boq_item_uri": uri,
        "item_no": item_no,
        "rule": {"basis": rule["basis"], "sample_group_qty": float(rule["group_qty"]), "match_prefix": rule["prefix"]},
        "design_quantity": float(design_qty),
        "expected_tests": expected,
        "qc_done": len(qc_rows),
        "lab_done": len(lab_rows),
        "dual_pass_done": dual_done,
        "missing_dual_pass": missing,
        "warning_level": "RED" if missing > 0 else "GREEN",
        "comparison": {"should_check": expected, "already_checked": dual_done, "missed_check": missing},
    }


def get_frequency_dashboard(*, sb: Any, project_uri: str, limit_items: int = 200) -> dict[str, Any]:
    rows = (
        sb.table("proof_utxo")
        .select("*")
        .eq("project_uri", project_uri)
        .order("created_at", desc=False)
        .limit(20000)
        .execute()
        .data
        or []
    )
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for row in rows:
        uri = _boq_uri(_as_dict(row))
        if not uri or uri in seen:
            continue
        seen.add(uri)
        if len(seen) > max(1, min(limit_items, 1000)):
            break
        try:
            items.append(calc_inspection_frequency(sb=sb, boq_item_uri=uri, project_uri=project_uri))
        except Exception:
            continue
    items.sort(key=lambda x: (-int(x.get("missing_dual_pass") or 0), _to_text(x.get("item_no"))))
    should_total = sum(int(x.get("expected_tests") or 0) for x in items)
    done_total = sum(int(x.get("dual_pass_done") or 0) for x in items)
    return {"ok": True, "project_uri": project_uri, "summary": {"should_check_total": should_total, "already_check_total": done_total, "missed_check_total": max(should_total - done_total, 0), "item_count": len(items), "red_items": sum(1 for x in items if _to_text(x.get("warning_level")) == "RED")}, "items": items}


def open_remediation_trip(*, sb: Any, fail_proof_id: str, notice: str, executor_uri: str = "v://executor/supervisor/system/", due_date: str = "", assignees: list[str] | None = None) -> dict[str, Any]:
    engine = ProofUTXOEngine(sb)
    fail = engine.get_by_id(fail_proof_id)
    if not fail:
        raise HTTPException(404, "fail proof not found")
    if _to_text(fail.get("result")).upper() != "FAIL":
        raise HTTPException(409, "remediation can only open for FAIL proof")
    rem_seed = _sha({"fail": fail_proof_id, "notice": notice, "due": due_date, "ts": _utc_iso()})
    rem_id = f"REM-{rem_seed[:12].upper()}"
    rem_row = engine.create(
        proof_id=f"GP-REM-{rem_seed[:16].upper()}",
        owner_uri=executor_uri,
        project_uri=_to_text(fail.get("project_uri")).strip(),
        project_id=fail.get("project_id"),
        proof_type="remediation",
        result="PENDING",
        state_data={"lifecycle_stage": "REMEDIATION_OPEN", "status": "OPEN", "remediation_id": rem_id, "root_fail_proof_id": fail_proof_id, "boq_item_uri": _boq_uri(_as_dict(fail)), "notice": notice or "Rectification required", "due_date": due_date, "assignees": [_to_text(x).strip() for x in _as_list(assignees) if _to_text(x).strip()], "opened_at": _utc_iso()},
        conditions=[],
        parent_proof_id=fail_proof_id,
        norm_uri="v://norm/CoordOS/Remediation/1.0#open",
        segment_uri=_to_text(fail.get("segment_uri")).strip(),
        signer_uri=executor_uri,
        signer_role="SUPERVISOR",
    )
    return {"ok": True, "remediation_id": rem_id, "remediation_proof_id": _to_text(rem_row.get("proof_id")).strip(), "fail_proof_id": fail_proof_id}


def remediation_reinspect(*, sb: Any, remediation_proof_id: str, result: str, payload: dict[str, Any] | None = None, executor_uri: str = "v://executor/inspector/system/") -> dict[str, Any]:
    engine = ProofUTXOEngine(sb)
    rem = engine.get_by_id(remediation_proof_id)
    if not rem:
        raise HTTPException(404, "remediation proof not found")
    rem_sd = _as_dict(rem.get("state_data"))
    if _to_text(rem_sd.get("status")).upper() not in {"OPEN", "REINSPECTED"}:
        raise HTTPException(409, "remediation is not open")
    fail_id = _to_text(rem_sd.get("root_fail_proof_id")).strip()
    fail = engine.get_by_id(fail_id)
    if not fail:
        raise HTTPException(404, "linked fail proof not found")
    if bool(fail.get("spent")):
        raise HTTPException(409, "linked fail proof already spent")
    res = _to_text(result).upper().strip()
    if res not in {"PASS", "FAIL", "OBSERVE"}:
        raise HTTPException(400, "result must be PASS/FAIL/OBSERVE")
    fail_sd = _as_dict(fail.get("state_data"))
    next_state = dict(fail_sd)
    next_state.update({"lifecycle_stage": "ENTRY", "status": "ENTRY", "trip_action": "remediation.reinspect", "remediation_id": _to_text(rem_sd.get("remediation_id")).strip(), "remediation_proof_id": remediation_proof_id, "reinspect_payload": _as_dict(payload), "reinspect_at": _utc_iso(), "remediation_unlock": res == "PASS"})
    tx = engine.consume(
        input_proof_ids=[fail_id],
        output_states=[{"owner_uri": _to_text(fail.get("owner_uri")).strip(), "project_id": fail.get("project_id"), "project_uri": _to_text(fail.get("project_uri")).strip(), "segment_uri": _to_text(fail.get("segment_uri")).strip(), "proof_type": "inspection", "result": res, "state_data": next_state, "conditions": _as_list(fail.get("conditions")), "parent_proof_id": fail_id, "norm_uri": _to_text(fail.get("norm_uri")).strip() or None}],
        executor_uri=executor_uri,
        executor_role="AI",
        trigger_action="Remediation.reinspect",
        trigger_data={"remediation_proof_id": remediation_proof_id, "fail_proof_id": fail_id, "result": res},
        tx_type="consume",
    )
    output_id = _to_text((_as_list(tx.get("output_proofs")) or [""])[0]).strip()
    return {"ok": True, "remediation_proof_id": remediation_proof_id, "fail_proof_id": fail_id, "reinspect_proof_id": output_id, "reinspect_result": res, "tx": tx}


def close_remediation_trip(*, sb: Any, remediation_proof_id: str, reinspection_proof_id: str, close_note: str = "", executor_uri: str = "v://executor/supervisor/system/") -> dict[str, Any]:
    engine = ProofUTXOEngine(sb)
    rem = engine.get_by_id(remediation_proof_id)
    if not rem:
        raise HTTPException(404, "remediation proof not found")
    if bool(rem.get("spent")):
        raise HTTPException(409, "remediation already closed")
    re_row = engine.get_by_id(reinspection_proof_id)
    if not re_row:
        raise HTTPException(404, "reinspection proof not found")
    if _to_text(re_row.get("result")).upper() != "PASS":
        raise HTTPException(409, "reinspection must be PASS before close")
    rem_sd = _as_dict(rem.get("state_data"))
    closed_state = dict(rem_sd)
    closed_state.update({"lifecycle_stage": "REMEDIATION_CLOSED", "status": "CLOSED", "closed_at": _utc_iso(), "close_note": close_note, "reinspection_proof_id": reinspection_proof_id})
    tx = engine.consume(
        input_proof_ids=[remediation_proof_id],
        output_states=[{"owner_uri": _to_text(rem.get("owner_uri")).strip(), "project_id": rem.get("project_id"), "project_uri": _to_text(rem.get("project_uri")).strip(), "segment_uri": _to_text(rem.get("segment_uri")).strip(), "proof_type": "remediation", "result": "PASS", "state_data": closed_state, "conditions": _as_list(rem.get("conditions")), "parent_proof_id": remediation_proof_id, "norm_uri": "v://norm/CoordOS/Remediation/1.0#close"}],
        executor_uri=executor_uri,
        executor_role="SUPERVISOR",
        trigger_action="Remediation.close",
        trigger_data={"remediation_proof_id": remediation_proof_id, "reinspection_proof_id": reinspection_proof_id},
        tx_type="archive",
    )
    return {"ok": True, "remediation_proof_id": remediation_proof_id, "closed_proof_id": _to_text((_as_list(tx.get('output_proofs')) or [''])[0]).strip(), "tx": tx}


def generate_railpact_payment_instruction(*, sb: Any, payment_id: str, executor_uri: str = "v://executor/owner/system/", auto_submit: bool = False) -> dict[str, Any]:
    engine = ProofUTXOEngine(sb)
    payment = engine.get_by_id(payment_id)
    if not payment:
        raise HTTPException(404, "payment proof not found")
    if _to_text(payment.get("proof_type")).lower() != "payment":
        raise HTTPException(409, "payment_id must reference payment proof")
    sd = _as_dict(payment.get("state_data"))
    summary = _as_dict(sd.get("summary"))
    if bool(summary.get("locked")):
        raise HTTPException(409, "payment certificate locked")
    payload = {
        "payment_id": payment_id,
        "project_uri": _to_text(payment.get("project_uri")).strip(),
        "period": _to_text(sd.get("period")).strip(),
        "artifact_uri": _to_text(sd.get("artifact_uri")).strip(),
        "amount_total": float(_to_float(summary.get("payable_amount_total")) or 0.0),
        "workflow": [
            {"step": 1, "name": "metering_apply", "status": "DONE"},
            {"step": 2, "name": "supervisor_verify", "status": "DONE"},
            {"step": 3, "name": "owner_approve", "status": "DONE" if auto_submit else "PENDING"},
            {"step": 4, "name": "railpact_pay", "status": "QUEUED" if auto_submit else "WAITING"},
        ],
        "issued_at": _utc_iso(),
    }
    h = _sha(payload)
    row = engine.create(
        proof_id=f"GP-RAIL-{h[:16].upper()}",
        owner_uri=executor_uri,
        project_uri=_to_text(payment.get("project_uri")).strip(),
        project_id=payment.get("project_id"),
        proof_type="payment_instruction",
        result="PASS" if auto_submit else "PENDING",
        state_data={"instruction_id": f"RP-{h[:16].upper()}", "instruction_hash": h, "railpact_uri": f"railpact://instruction/RP-{h[:16].upper()}", "payment_id": payment_id, "instruction_payload": payload, "workflow": payload["workflow"]},
        conditions=[],
        parent_proof_id=payment_id,
        norm_uri="v://norm/RailPact/1.0#payment_instruction",
        segment_uri=_to_text(payment.get("segment_uri")).strip(),
        signer_uri=executor_uri,
        signer_role="OWNER",
    )
    return {"ok": True, "payment_id": payment_id, "instruction_id": f"RP-{h[:16].upper()}", "instruction_hash": h, "railpact_uri": f"railpact://instruction/RP-{h[:16].upper()}", "proof_id": _to_text(row.get("proof_id")).strip(), "proof_hash": _to_text(row.get("proof_hash")).strip(), "workflow": payload["workflow"]}

"""Material IQC runtime for process-chain gating."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from fastapi import HTTPException
try:
    import yaml
except Exception:  # pragma: no cover - optional dependency
    yaml = None

from services.api.domain.boqpeg.models import IQCResult, MaterialRequirement
from services.api.domain.utxo.integrations import ProofUTXOEngine

_MATERIAL_CONFIG_CACHE: list[MaterialRequirement] | None = None


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    text = _to_text(value).strip()
    if text:
        return text
    return _utc_now().isoformat()


def _sha16(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _material_config_path() -> Path:
    return _repo_root() / "configs" / "process_chains" / "drilled-pile-materials.yaml"


def _fallback_material_requirements() -> list[MaterialRequirement]:
    rows = [
        {
            "step_id": "pile-prepare-01",
            "material_code": "steel-casing",
            "material_name": "Steel casing",
            "iqc_form_code": "IQC-Steel",
            "required": True,
            "inspection_batch_required": False,
            "min_qty": 0.0,
        },
        {
            "step_id": "pile-hole-02",
            "material_code": "slurry-material",
            "material_name": "Slurry material",
            "iqc_form_code": "IQC-Slurry",
            "required": True,
            "inspection_batch_required": False,
            "min_qty": 0.0,
        },
        {
            "step_id": "pile-rebar-03",
            "material_code": "rebar-cage",
            "material_name": "Rebar cage",
            "iqc_form_code": "IQC-RebarCage",
            "required": True,
            "inspection_batch_required": False,
            "min_qty": 0.0,
        },
        {
            "step_id": "pile-pour-04",
            "material_code": "concrete-c50",
            "material_name": "Concrete C50",
            "iqc_form_code": "IQC-Concrete",
            "required": True,
            "inspection_batch_required": True,
            "min_qty": 25.0,
        },
        {
            "step_id": "pile-pour-04",
            "material_code": "rebar-hrb400",
            "material_name": "Rebar HRB400",
            "iqc_form_code": "IQC-Rebar",
            "required": True,
            "inspection_batch_required": True,
            "min_qty": 0.0,
        },
    ]
    return [MaterialRequirement.model_validate(item) for item in rows]


def _load_material_config() -> list[MaterialRequirement]:
    global _MATERIAL_CONFIG_CACHE
    if _MATERIAL_CONFIG_CACHE is not None:
        return [item.model_copy(deep=True) for item in _MATERIAL_CONFIG_CACHE]

    rows: list[MaterialRequirement] = []
    path = _material_config_path()
    if path.exists():
        try:
            raw = path.read_text(encoding="utf-8").strip()
            payload: Any
            if not raw:
                payload = []
            else:
                try:
                    payload = json.loads(raw)
                except Exception:
                    payload = yaml.safe_load(raw) if yaml is not None else []
            items = payload.get("requirements") if isinstance(payload, dict) else payload
            for item in _as_list(items):
                if not isinstance(item, dict):
                    continue
                rows.append(MaterialRequirement.model_validate(item))
        except Exception:
            rows = []
    if not rows:
        rows = _fallback_material_requirements()
    _MATERIAL_CONFIG_CACHE = [item.model_copy(deep=True) for item in rows]
    return [item.model_copy(deep=True) for item in rows]


def load_drilled_pile_material_requirements() -> list[MaterialRequirement]:
    return _load_material_config()


def material_requirements_by_step(
    requirements: list[MaterialRequirement] | None = None,
) -> dict[str, list[MaterialRequirement]]:
    rows = requirements if requirements is not None else load_drilled_pile_material_requirements()
    grouped: dict[str, list[MaterialRequirement]] = {}
    for item in rows:
        grouped.setdefault(_to_text(item.step_id).strip(), []).append(item.model_copy(deep=True))
    return grouped


def _safe_uri_token(value: str) -> str:
    text = _to_text(value).strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^0-9a-zA-Z._-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "na"


def _proof_result_from_status(status: str) -> str:
    token = _to_text(status).strip().lower()
    if token == "approved":
        return "PASS"
    if token == "rejected":
        return "FAIL"
    return "WARNING"


def _proof_status(value: Any) -> str:
    token = _to_text(value).strip().lower()
    if token in {"approved", "rejected", "pending"}:
        return token
    if token in {"pass", "ok", "passed"}:
        return "approved"
    if token in {"fail", "failed", "error"}:
        return "rejected"
    return "pending"


def _proof_hash_preview(state_data: dict[str, Any]) -> str:
    payload = json.dumps(state_data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _create_iqc_proof(
    *,
    sb: Any,
    commit: bool,
    proof_id: str,
    owner_uri: str,
    project_uri: str,
    component_uri: str,
    material_code: str,
    state_data: dict[str, Any],
    result: str,
) -> dict[str, Any]:
    preview = {
        "proof_id": proof_id,
        "proof_hash": _proof_hash_preview(state_data),
        "proof_type": "inspection",
        "segment_uri": f"{component_uri.rstrip('/')}/iqc/{material_code}",
        "result": result,
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
        norm_uri="v://norm/NormPeg/IQC/1.0",
        segment_uri=preview["segment_uri"],
        signer_uri=_to_text(state_data.get("executor_uri")).strip() or owner_uri,
        signer_role="IQC",
    )
    return {
        **preview,
        "proof_hash": _to_text(row.get("proof_hash")).strip() or preview["proof_hash"],
        "committed": True,
        "row": row,
    }


def submit_iqc(
    *,
    sb: Any,
    project_uri: str,
    component_uri: str,
    step_id: str,
    material_code: str,
    material_name: str,
    iqc_form_code: str,
    batch_no: str,
    total_qty: float,
    unit: str,
    unit_price: float,
    supplier: str,
    test_results: dict[str, Any] | None,
    executor_uri: str,
    owner_uri: str,
    status: str,
    commit: bool = True,
) -> IQCResult:
    p_uri = _to_text(project_uri).strip().rstrip("/")
    c_uri = _to_text(component_uri).strip().rstrip("/")
    m_code = _safe_uri_token(material_code)
    b_no = _safe_uri_token(batch_no)
    if not p_uri:
        raise HTTPException(status_code=400, detail="project_uri is required")
    if not c_uri:
        raise HTTPException(status_code=400, detail="component_uri is required")
    if not _to_text(material_code).strip():
        raise HTTPException(status_code=400, detail="material_code is required")
    if not _to_text(batch_no).strip():
        raise HTTPException(status_code=400, detail="batch_no is required")
    e_uri = _to_text(executor_uri).strip()
    if not e_uri:
        raise HTTPException(status_code=400, detail="executor_uri is required")
    final_status = _proof_status(status)
    iqc_uri = f"v://cost/iqc/{m_code}-{b_no}"
    submitted_at = _utc_now()
    resolved_owner = _to_text(owner_uri).strip() or f"{p_uri}/role/system/"
    state_data = {
        "proof_kind": "iqc_material_submit",
        "project_uri": p_uri,
        "component_uri": c_uri,
        "step_id": _to_text(step_id).strip(),
        "material_code": _to_text(material_code).strip(),
        "material_name": _to_text(material_name).strip(),
        "iqc_form_code": _to_text(iqc_form_code).strip(),
        "batch_no": _to_text(batch_no).strip(),
        "total_qty": float(total_qty or 0.0),
        "unit": _to_text(unit).strip(),
        "unit_price": float(unit_price or 0.0),
        "supplier": _to_text(supplier).strip(),
        "status": final_status,
        "iqc_uri": iqc_uri,
        "executor_uri": e_uri,
        "test_results": _as_dict(test_results),
        "submitted_at": submitted_at.isoformat(),
    }
    proof_id = f"GP-IQC-{_sha16(f'{p_uri}:{c_uri}:{m_code}:{b_no}:{submitted_at.isoformat()}').upper()}"
    proof = _create_iqc_proof(
        sb=sb,
        commit=bool(commit),
        proof_id=proof_id,
        owner_uri=resolved_owner,
        project_uri=p_uri,
        component_uri=c_uri,
        material_code=m_code,
        state_data=state_data,
        result=_proof_result_from_status(final_status),
    )
    return IQCResult(
        material_code=_to_text(material_code).strip(),
        material_name=_to_text(material_name).strip() or _to_text(material_code).strip(),
        iqc_form_code=_to_text(iqc_form_code).strip(),
        batch_no=_to_text(batch_no).strip(),
        total_qty=float(total_qty or 0.0),
        unit=_to_text(unit).strip(),
        unit_price=float(unit_price or 0.0),
        supplier=_to_text(supplier).strip(),
        status=final_status,
        iqc_uri=iqc_uri,
        submitted_at=submitted_at,
        proof_id=_to_text(proof.get("proof_id")).strip(),
        proof_hash=_to_text(proof.get("proof_hash")).strip(),
        committed=bool(proof.get("committed")),
        component_uri=c_uri,
        project_uri=p_uri,
        executor_uri=e_uri,
    )


def _fetch_iqc_rows(*, sb: Any, project_uri: str) -> list[dict[str, Any]]:
    if sb is None:
        return []
    rows = (
        sb.table("proof_utxo")
        .select("*")
        .eq("project_uri", _to_text(project_uri).strip())
        .eq("proof_type", "inspection")
        .order("created_at", desc=False)
        .limit(20000)
        .execute()
        .data
        or []
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        state_data = _as_dict(row.get("state_data"))
        if _to_text(state_data.get("proof_kind")).strip() != "iqc_material_submit":
            continue
        out.append(row)
    return out


def build_component_material_state(
    *,
    sb: Any,
    project_uri: str,
    component_uri: str,
) -> dict[str, dict[str, Any]]:
    c_uri = _to_text(component_uri).strip().rstrip("/")
    if not c_uri:
        return {}
    latest: dict[str, dict[str, Any]] = {}
    for row in _fetch_iqc_rows(sb=sb, project_uri=project_uri):
        state_data = _as_dict(row.get("state_data"))
        if _to_text(state_data.get("component_uri")).strip().rstrip("/") != c_uri:
            continue
        material_code = _to_text(state_data.get("material_code")).strip()
        if not material_code:
            continue
        key = material_code.lower()
        marker = _to_iso(state_data.get("submitted_at") or row.get("created_at"))
        previous = latest.get(key)
        previous_marker = _to_iso(_as_dict(previous).get("submitted_at")) if previous else ""
        if previous and previous_marker >= marker:
            continue
        latest[key] = {
            "material_code": material_code,
            "material_name": _to_text(state_data.get("material_name")).strip(),
            "iqc_form_code": _to_text(state_data.get("iqc_form_code")).strip(),
            "batch_no": _to_text(state_data.get("batch_no")).strip(),
            "status": _proof_status(state_data.get("status")),
            "iqc_uri": _to_text(state_data.get("iqc_uri")).strip(),
            "total_qty": float(state_data.get("total_qty") or 0.0),
            "unit": _to_text(state_data.get("unit")).strip(),
            "unit_price": float(state_data.get("unit_price") or 0.0),
            "supplier": _to_text(state_data.get("supplier")).strip(),
            "executor_uri": _to_text(state_data.get("executor_uri")).strip(),
            "submitted_at": marker,
            "proof_id": _to_text(row.get("proof_id")).strip(),
            "proof_hash": _to_text(row.get("proof_hash")).strip(),
            "step_id": _to_text(state_data.get("step_id")).strip(),
        }
    return latest


def map_requirements_with_state(
    requirements: list[MaterialRequirement],
    state_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in requirements:
        key = _to_text(item.material_code).strip().lower()
        state = _as_dict(state_map.get(key))
        out.append(
            {
                "step_id": item.step_id,
                "material_code": item.material_code,
                "material_name": item.material_name,
                "iqc_form_code": item.iqc_form_code,
                "required": bool(item.required),
                "min_qty": float(item.min_qty),
                "inspection_batch_required": bool(item.inspection_batch_required),
                "status": _proof_status(state.get("status") or item.status),
                "iqc_uri": _to_text(state.get("iqc_uri") or item.iqc_uri).strip(),
                "total_qty": float(state.get("total_qty") or 0.0),
                "unit": _to_text(state.get("unit")).strip(),
                "unit_price": float(state.get("unit_price") or 0.0),
                "supplier": _to_text(state.get("supplier")).strip(),
                "batch_no": _to_text(state.get("batch_no")).strip(),
                "executor_uri": _to_text(state.get("executor_uri")).strip(),
                "submitted_at": _to_text(state.get("submitted_at")).strip(),
                "proof_id": _to_text(state.get("proof_id")).strip(),
                "proof_hash": _to_text(state.get("proof_hash")).strip(),
            }
        )
    return out

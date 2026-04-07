"""Bridge construction process-chain engine for table sequencing and closure."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import re
from typing import Any

from fastapi import HTTPException

from services.api.domain.utxo.integrations import ProofUTXOEngine


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


def _normalize_bridge_slug(name: str) -> str:
    text = _to_text(name).strip().lower().replace("\\", "-").replace("/", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff_-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "bridge"


def _normalize_pile_token(value: str) -> str:
    text = _to_text(value).strip().replace("\\", "-").replace("/", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff_-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "P1"


def _sha16(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _normalize_table_name(value: Any) -> str:
    text = _to_text(value).strip()
    text = re.sub(r"\s+", "", text)
    return text


def _uniq_tables(raw: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in _as_list(raw):
        token = _normalize_table_name(item)
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


@dataclass(slots=True)
class ProcessStep:
    step_id: str
    order: int
    name: str
    required_tables: list[str] = field(default_factory=list)
    pre_conditions: list[str] = field(default_factory=list)
    normref_uris: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    boq_item_ref: str = ""
    component_uri: str = ""


@dataclass(slots=True)
class ProcessChain:
    chain_id: str
    project_uri: str
    bridge_uri: str
    component_uri: str
    component_type: str
    chain_kind: str
    boq_item_ref: str = ""
    steps: list[ProcessStep] = field(default_factory=list)
    current_step: str = ""
    completed_tables: dict[str, dict[str, Any]] = field(default_factory=dict)
    state_matrix: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    updated_at: str = ""


def _default_drilled_pile_steps(*, component_uri: str, boq_item_ref: str = "") -> list[ProcessStep]:
    raw = [
        {
            "step_id": "pile-prepare-01",
            "order": 1,
            "name": "准备阶段",
            "required_tables": ["桥施2表"],
            "pre_conditions": [],
            "normref_uris": ["v://normref.com/qc/pile-foundation@v1"],
        },
        {
            "step_id": "pile-hole-02",
            "order": 2,
            "name": "成孔阶段",
            "required_tables": ["桥施7表"],
            "pre_conditions": ["桥施2表"],
            "normref_uris": ["v://normref.com/qc/pile-foundation@v1"],
        },
        {
            "step_id": "pile-rebar-03",
            "order": 3,
            "name": "钢筋笼阶段",
            "required_tables": ["桥施46表", "桥施47表"],
            "pre_conditions": ["桥施7表"],
            "normref_uris": ["v://normref.com/qc/rebar-processing@v1"],
        },
        {
            "step_id": "pile-pour-04",
            "order": 4,
            "name": "混凝土浇筑阶段",
            "required_tables": ["桥施混凝土浇筑记录表", "桥施坍落度检查记录"],
            "pre_conditions": ["桥施46表", "桥施47表"],
            "normref_uris": ["v://normref.com/qc/concrete-compressive-test@v1"],
        },
        {
            "step_id": "pile-acceptance-05",
            "order": 5,
            "name": "成桩验收阶段",
            "required_tables": ["桥施桩基承载力检测表", "桥施桩基完整性检测记录"],
            "pre_conditions": ["桥施混凝土浇筑记录表", "桥施坍落度检查记录"],
            "normref_uris": ["v://normref.com/qc/pile-foundation@v1"],
        },
        {
            "step_id": "pile-subitem-06",
            "order": 6,
            "name": "分项分部验收",
            "required_tables": ["隐蔽工程验收记录", "分项工程质量验收记录表"],
            "pre_conditions": ["桥施桩基承载力检测表", "桥施桩基完整性检测记录"],
            "normref_uris": ["v://normref.com/schema/qc-v1"],
        },
    ]
    out: list[ProcessStep] = []
    for idx, item in enumerate(raw, start=1):
        out.append(
            ProcessStep(
                step_id=_to_text(item.get("step_id")).strip() or f"step-{idx}",
                order=int(item.get("order") or idx),
                name=_to_text(item.get("name")).strip() or f"Step {idx}",
                required_tables=_uniq_tables(item.get("required_tables")),
                pre_conditions=_uniq_tables(item.get("pre_conditions")),
                normref_uris=[_to_text(x).strip() for x in _as_list(item.get("normref_uris")) if _to_text(x).strip()],
                next_steps=[],
                boq_item_ref=boq_item_ref,
                component_uri=component_uri,
            )
        )
    for idx, step in enumerate(out):
        if idx + 1 < len(out):
            step.next_steps = [out[idx + 1].step_id]
    return out


def _normalize_steps(raw: Any, *, component_uri: str, boq_item_ref: str = "") -> list[ProcessStep]:
    if not isinstance(raw, list) or not raw:
        return _default_drilled_pile_steps(component_uri=component_uri, boq_item_ref=boq_item_ref)
    out: list[ProcessStep] = []
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        step_id = _to_text(item.get("step_id")).strip() or f"step-{idx}"
        out.append(
            ProcessStep(
                step_id=step_id,
                order=int(item.get("order") or idx),
                name=_to_text(item.get("name")).strip() or f"Step {idx}",
                required_tables=_uniq_tables(item.get("required_tables")),
                pre_conditions=_uniq_tables(item.get("pre_conditions")),
                normref_uris=[_to_text(x).strip() for x in _as_list(item.get("normref_uris")) if _to_text(x).strip()],
                next_steps=[_to_text(x).strip() for x in _as_list(item.get("next_steps")) if _to_text(x).strip()],
                boq_item_ref=_to_text(item.get("boq_item_ref")).strip() or boq_item_ref,
                component_uri=_to_text(item.get("component_uri")).strip() or component_uri,
            )
        )
    out.sort(key=lambda x: (x.order, x.step_id))
    if not out:
        return _default_drilled_pile_steps(component_uri=component_uri, boq_item_ref=boq_item_ref)
    for idx, step in enumerate(out):
        if not step.next_steps and idx + 1 < len(out):
            step.next_steps = [out[idx + 1].step_id]
    return out


def _table_passed(completed_tables: dict[str, dict[str, Any]], table_name: str) -> bool:
    entry = _as_dict(completed_tables.get(_normalize_table_name(table_name)))
    result = _to_text(entry.get("result")).strip().upper()
    return result == "PASS"


def _step_is_completed(step: ProcessStep, completed_tables: dict[str, dict[str, Any]]) -> bool:
    if not step.required_tables:
        return all(_table_passed(completed_tables, pre) for pre in step.pre_conditions)
    return all(_table_passed(completed_tables, table) for table in step.required_tables)


def _step_is_available(step: ProcessStep, completed_tables: dict[str, dict[str, Any]]) -> bool:
    if _step_is_completed(step, completed_tables):
        return False
    return all(_table_passed(completed_tables, pre) for pre in step.pre_conditions)


def _recompute_chain(chain: ProcessChain) -> ProcessChain:
    steps = sorted(chain.steps, key=lambda x: (x.order, x.step_id))
    completed_steps: list[str] = []
    available_steps: list[str] = []
    blocked_steps: list[dict[str, Any]] = []
    total_tables = 0
    done_tables = 0
    for step in steps:
        total_tables += len(step.required_tables)
        for table in step.required_tables:
            if _table_passed(chain.completed_tables, table):
                done_tables += 1
        if _step_is_completed(step, chain.completed_tables):
            completed_steps.append(step.step_id)
            continue
        missing_pre = [pre for pre in step.pre_conditions if not _table_passed(chain.completed_tables, pre)]
        if missing_pre:
            blocked_steps.append({"step_id": step.step_id, "name": step.name, "missing_pre_conditions": missing_pre})
        else:
            available_steps.append(step.step_id)
    current_step = ""
    for step in steps:
        if step.step_id not in completed_steps:
            current_step = step.step_id
            break
    pending_tables = max(total_tables - done_tables, 0)
    chain.current_step = current_step
    chain.state_matrix = {
        "total_steps": len(steps),
        "completed_steps": len(completed_steps),
        "available_steps": len(available_steps),
        "blocked_steps": len(blocked_steps),
        "total_tables": total_tables,
        "completed_tables": done_tables,
        "pending_tables": pending_tables,
        "completion_ratio": round((len(completed_steps) / len(steps) * 100.0), 4) if steps else 0.0,
        "finalproof_ready": bool(steps) and len(completed_steps) == len(steps),
        "current_step": current_step,
    }
    chain.steps = steps
    return chain


def _chain_state(chain: ProcessChain, *, action: str) -> dict[str, Any]:
    payload = asdict(chain)
    payload.update({"entity_type": "process_chain", "action": action})
    return payload


def _create_proof(
    *,
    sb: Any,
    commit: bool,
    proof_id: str,
    owner_uri: str,
    project_uri: str,
    proof_type: str,
    result: str,
    segment_uri: str,
    norm_uri: str,
    state_data: dict[str, Any],
) -> dict[str, Any]:
    preview = {
        "proof_id": proof_id,
        "proof_type": proof_type,
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
        proof_type=proof_type,
        result=result,
        state_data=state_data,
        norm_uri=norm_uri,
        segment_uri=segment_uri,
        signer_uri=owner_uri,
        signer_role="SYSTEM",
    )
    return {**preview, "committed": True, "row": row}


def _fetch_node_rows(*, sb: Any, project_uri: str) -> list[dict[str, Any]]:
    if sb is None:
        return []
    try:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("project_uri", _to_text(project_uri).strip())
            .eq("proof_type", "node")
            .order("created_at", desc=False)
            .limit(20000)
            .execute()
            .data
            or []
        )
        return [row for row in rows if isinstance(row, dict)]
    except Exception as exc:
        raise HTTPException(502, f"failed to query process chains: {exc}") from exc


def _latest_process_chains(*, sb: Any, project_uri: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in _fetch_node_rows(sb=sb, project_uri=project_uri):
        sd = _as_dict(row.get("state_data"))
        if _to_text(sd.get("entity_type")).strip() != "process_chain":
            continue
        component_uri = _to_text(sd.get("component_uri")).strip().rstrip("/")
        if component_uri:
            latest[component_uri] = sd
    return latest


def _require_project_uri(value: str) -> str:
    uri = _to_text(value).strip().rstrip("/")
    if not uri:
        raise HTTPException(400, "project_uri is required")
    return uri


def _require_component_uri(value: str) -> str:
    uri = _to_text(value).strip().rstrip("/")
    if not uri:
        raise HTTPException(400, "component_uri is required")
    return uri


def _resolve_owner_uri(*, project_uri: str, owner_uri: str) -> str:
    owner = _to_text(owner_uri).strip()
    return owner or f"{project_uri.rstrip('/')}/role/system/"


def create_process_chain(
    *,
    sb: Any,
    project_uri: str,
    component_uri: str,
    bridge_uri: str = "",
    component_type: str = "",
    chain_kind: str = "drilled_pile",
    boq_item_ref: str = "",
    steps: list[dict[str, Any]] | None = None,
    completed_tables: dict[str, dict[str, Any]] | None = None,
    owner_uri: str = "",
    commit: bool = False,
) -> dict[str, Any]:
    p_uri = _require_project_uri(project_uri)
    c_uri = _require_component_uri(component_uri)
    normalized_owner = _resolve_owner_uri(project_uri=p_uri, owner_uri=owner_uri)
    now = datetime.now(UTC).isoformat()
    latest = _latest_process_chains(sb=sb, project_uri=p_uri).get(c_uri.rstrip("/"))
    version = int(_as_dict(latest).get("version") or 0) + 1 if latest else 1
    chain = ProcessChain(
        chain_id=f"CHAIN-{_sha16(f'{c_uri}:{chain_kind}:{now}').upper()}",
        project_uri=p_uri,
        bridge_uri=_to_text(bridge_uri).strip().rstrip("/"),
        component_uri=c_uri,
        component_type=_to_text(component_type).strip() or "drilled_pile",
        chain_kind=_to_text(chain_kind).strip() or "drilled_pile",
        boq_item_ref=_to_text(boq_item_ref).strip(),
        steps=_normalize_steps(steps, component_uri=c_uri, boq_item_ref=_to_text(boq_item_ref).strip()),
        current_step="",
        completed_tables={_normalize_table_name(k): _as_dict(v) for k, v in _as_dict(completed_tables).items()},
        state_matrix={},
        version=max(version, 1),
        updated_at=now,
    )
    chain = _recompute_chain(chain)
    entity_proof = _create_proof(
        sb=sb,
        commit=bool(commit),
        proof_id=f"GP-PROCESS-CHAIN-{_sha16(f'{chain.chain_id}:entity').upper()}",
        owner_uri=normalized_owner,
        project_uri=p_uri,
        proof_type="node",
        result="PASS",
        segment_uri=f"{c_uri}/process-chain/main",
        norm_uri="v://norm/NormPeg/ProcessChain/1.0",
        state_data=_chain_state(chain, action="process_chain_compiled"),
    )
    return {
        "ok": True,
        "project_uri": p_uri,
        "component_uri": c_uri,
        "chain_uri": f"{c_uri}/process-chain/main",
        "chain": _chain_state(chain, action="process_chain_compiled"),
        "proofs": {"entity_proof": entity_proof},
    }


def get_process_chain(
    *,
    sb: Any,
    project_uri: str,
    component_uri: str,
    chain_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    p_uri = _require_project_uri(project_uri)
    c_uri = _require_component_uri(component_uri)
    source = _as_dict(chain_snapshot) if isinstance(chain_snapshot, dict) else _latest_process_chains(sb=sb, project_uri=p_uri).get(c_uri.rstrip("/"))
    if not source:
        raise HTTPException(404, "process chain not found")
    chain = ProcessChain(
        chain_id=_to_text(source.get("chain_id")).strip() or f"CHAIN-{_sha16(c_uri).upper()}",
        project_uri=p_uri,
        bridge_uri=_to_text(source.get("bridge_uri")).strip(),
        component_uri=c_uri,
        component_type=_to_text(source.get("component_type")).strip() or "drilled_pile",
        chain_kind=_to_text(source.get("chain_kind")).strip() or "drilled_pile",
        boq_item_ref=_to_text(source.get("boq_item_ref")).strip(),
        steps=_normalize_steps(source.get("steps"), component_uri=c_uri, boq_item_ref=_to_text(source.get("boq_item_ref")).strip()),
        current_step=_to_text(source.get("current_step")).strip(),
        completed_tables={_normalize_table_name(k): _as_dict(v) for k, v in _as_dict(source.get("completed_tables")).items()},
        state_matrix=_as_dict(source.get("state_matrix")),
        version=max(int(source.get("version") or 1), 1),
        updated_at=_to_text(source.get("updated_at")).strip() or datetime.now(UTC).isoformat(),
    )
    chain = _recompute_chain(chain)
    return {
        "ok": True,
        "project_uri": p_uri,
        "component_uri": c_uri,
        "chain_uri": f"{c_uri}/process-chain/main",
        "chain": _chain_state(chain, action="process_chain_loaded"),
    }


def _find_step_by_table(chain: ProcessChain, table_name: str) -> ProcessStep | None:
    token = _normalize_table_name(table_name)
    for step in chain.steps:
        if token in step.required_tables:
            return step
    return None


def submit_process_table(
    *,
    sb: Any,
    project_uri: str,
    component_uri: str,
    table_name: str,
    proof_hash: str,
    result: str = "PASS",
    owner_uri: str = "",
    commit: bool = False,
    chain_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    loaded = get_process_chain(
        sb=sb,
        project_uri=project_uri,
        component_uri=component_uri,
        chain_snapshot=chain_snapshot,
    )
    source = _as_dict(loaded.get("chain"))
    chain = ProcessChain(
        chain_id=_to_text(source.get("chain_id")).strip(),
        project_uri=_to_text(source.get("project_uri")).strip(),
        bridge_uri=_to_text(source.get("bridge_uri")).strip(),
        component_uri=_to_text(source.get("component_uri")).strip(),
        component_type=_to_text(source.get("component_type")).strip() or "drilled_pile",
        chain_kind=_to_text(source.get("chain_kind")).strip() or "drilled_pile",
        boq_item_ref=_to_text(source.get("boq_item_ref")).strip(),
        steps=_normalize_steps(source.get("steps"), component_uri=_to_text(source.get("component_uri")).strip(), boq_item_ref=_to_text(source.get("boq_item_ref")).strip()),
        current_step=_to_text(source.get("current_step")).strip(),
        completed_tables={_normalize_table_name(k): _as_dict(v) for k, v in _as_dict(source.get("completed_tables")).items()},
        state_matrix=_as_dict(source.get("state_matrix")),
        version=max(int(source.get("version") or 1), 1),
        updated_at=_to_text(source.get("updated_at")).strip(),
    )
    chain = _recompute_chain(chain)
    normalized_table = _normalize_table_name(table_name)
    if not normalized_table:
        raise HTTPException(400, "table_name is required")
    if not _to_text(proof_hash).strip():
        raise HTTPException(400, "proof_hash is required")
    step = _find_step_by_table(chain, normalized_table)
    if step is None:
        raise HTTPException(400, f"table not in chain: {table_name}")
    missing_pre = [pre for pre in step.pre_conditions if not _table_passed(chain.completed_tables, pre)]
    if missing_pre:
        raise HTTPException(409, f"pre conditions not passed: {', '.join(missing_pre)}")
    normalized_result = _to_text(result).strip().upper() or "PASS"
    chain.completed_tables[normalized_table] = {
        "table_name": normalized_table,
        "proof_hash": _to_text(proof_hash).strip(),
        "result": normalized_result,
        "submitted_at": datetime.now(UTC).isoformat(),
        "step_id": step.step_id,
    }
    chain.version = max(chain.version + 1, 1)
    chain.updated_at = datetime.now(UTC).isoformat()
    chain = _recompute_chain(chain)

    normalized_owner = _resolve_owner_uri(project_uri=chain.project_uri, owner_uri=owner_uri)
    chain_state = _chain_state(chain, action="process_chain_table_submit")
    chain_proof = _create_proof(
        sb=sb,
        commit=bool(commit),
        proof_id=f"GP-PROCESS-CHAIN-{_sha16(f'{chain.chain_id}:{chain.version}').upper()}",
        owner_uri=normalized_owner,
        project_uri=chain.project_uri,
        proof_type="node",
        result="PASS",
        segment_uri=f"{chain.component_uri}/process-chain/main",
        norm_uri="v://norm/NormPeg/ProcessChain/1.0",
        state_data=chain_state,
    )
    table_proof = _create_proof(
        sb=sb,
        commit=bool(commit),
        proof_id=f"GP-PROCESS-TABLE-{_sha16(f'{chain.chain_id}:{normalized_table}:{chain.version}').upper()}",
        owner_uri=normalized_owner,
        project_uri=chain.project_uri,
        proof_type="inspection",
        result=normalized_result if normalized_result in {"PASS", "FAIL", "WARNING"} else "PASS",
        segment_uri=f"{chain.component_uri}/process-chain/tables/{normalized_table}",
        norm_uri="v://norm/NormPeg/ProcessChainTable/1.0",
        state_data={
            "proof_kind": "process_chain_table_submit",
            "chain_id": chain.chain_id,
            "component_uri": chain.component_uri,
            "step_id": step.step_id,
            "table_name": normalized_table,
            "table_result": normalized_result,
            "source_proof_hash": _to_text(proof_hash).strip(),
        },
    )

    finalproof = None
    boq_state_update = {}
    if bool(chain.state_matrix.get("finalproof_ready")):
        finalproof = _create_proof(
            sb=sb,
            commit=bool(commit),
            proof_id=f"GP-FINALPROOF-{_sha16(f'{chain.chain_id}:{chain.updated_at}').upper()}",
            owner_uri=normalized_owner,
            project_uri=chain.project_uri,
            proof_type="report",
            result="PASS",
            segment_uri=f"{chain.component_uri}/finalproof",
            norm_uri="v://norm/NormPeg/FinalProof/1.0",
            state_data={
                "proof_kind": "process_chain_finalproof",
                "chain_id": chain.chain_id,
                "component_uri": chain.component_uri,
                "completed_steps": chain.state_matrix.get("completed_steps", 0),
                "total_steps": chain.state_matrix.get("total_steps", 0),
            },
        )
        boq_state_update = {
            "target_boq_item_uri": chain.boq_item_ref,
            "state_matrix_delta": {"signed": 1, "pending": -1},
            "reason": "component process chain reached FinalProof",
        }
    return {
        "ok": True,
        "project_uri": chain.project_uri,
        "component_uri": chain.component_uri,
        "chain_uri": f"{chain.component_uri}/process-chain/main",
        "chain": chain_state,
        "submission": {
            "step_id": step.step_id,
            "table_name": normalized_table,
            "result": normalized_result,
            "current_step": chain.current_step,
            "finalproof_ready": bool(chain.state_matrix.get("finalproof_ready")),
        },
        "boq_state_update": boq_state_update,
        "proofs": {
            "chain_proof": chain_proof,
            "table_submission_proof": table_proof,
            "finalproof": finalproof,
        },
    }


def pile_component_uri(project_uri: str, bridge_name: str, pile_id: str) -> str:
    p_uri = _require_project_uri(project_uri)
    slug = _normalize_bridge_slug(_to_text(bridge_name).strip())
    pile = _normalize_pile_token(_to_text(pile_id).strip())
    return f"{p_uri.rstrip('/')}/bridge/{slug}/pile/{pile}"


__all__ = [
    "ProcessChain",
    "ProcessStep",
    "create_process_chain",
    "get_process_chain",
    "pile_component_uri",
    "submit_process_table",
]


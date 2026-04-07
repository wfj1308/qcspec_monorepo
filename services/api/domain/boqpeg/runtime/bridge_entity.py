"""Bridge/Pile sovereign entity engines with hierarchical aggregation."""

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


def _to_int(value: Any, default: int = 0) -> int:
    text = _to_text(value).strip().replace(",", "")
    if not text:
        return int(default)
    try:
        return int(float(text))
    except Exception:
        return int(default)


def _to_float(value: Any, default: float = 0.0) -> float:
    text = _to_text(value).strip().replace(",", "")
    if not text:
        return float(default)
    try:
        return float(text)
    except Exception:
        return float(default)


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


def _sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _tail_token(uri: str) -> str:
    text = _to_text(uri).strip().rstrip("/")
    return text.split("/")[-1] if text else ""


def _bridge_uri(project_uri: str, bridge_slug: str) -> str:
    return f"{_to_text(project_uri).strip().rstrip('/')}/bridge/{bridge_slug}"


def _pile_uri(bridge_uri: str, pile_id: str) -> str:
    return f"{_to_text(bridge_uri).strip().rstrip('/')}/pile/{_normalize_pile_token(pile_id)}"


def _is_pile_like(item: dict[str, Any]) -> bool:
    blob = " ".join(
        [
            _to_text(item.get("component_type")).strip().lower(),
            _to_text(item.get("component_uri")).strip().lower(),
            _to_text(item.get("pile_uri")).strip().lower(),
            _to_text(item.get("boq_code")).strip().lower(),
            _to_text(item.get("description")).strip().lower(),
            _to_text(item.get("item_name")).strip().lower(),
        ]
    )
    if "pile" in blob:
        return True
    code = _to_text(item.get("boq_code")).strip()
    return code.startswith("402") or code.startswith("403")


def _derive_lifecycle_stage(*, total: int, generated: int, signed: int, pending: int, override: str = "") -> str:
    direct = _to_text(override).strip().lower()
    if direct:
        return direct
    if total > 0 and pending <= 0 and signed >= max(generated, 0):
        return "completed"
    if generated > 0 or signed > 0:
        return "in_progress"
    return "draft"


def _normalize_pile_state_matrix(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, int]:
    b = _as_dict(base)
    u = _as_dict(updates)
    total = _to_int(u.get("total_qc_tables"), _to_int(b.get("total_qc_tables"), 0))
    generated = _to_int(u.get("generated"), _to_int(b.get("generated"), 0))
    signed = _to_int(u.get("signed"), _to_int(b.get("signed"), 0))
    pending = _to_int(u.get("pending"), max(total - generated, 0)) if "pending" in u else max(total - generated, 0)
    return {
        "total_qc_tables": max(total, 0),
        "generated": max(generated, 0),
        "signed": max(signed, 0),
        "pending": max(pending, 0),
    }


def _bridge_state_matrix_from_piles(piles: list[dict[str, Any]]) -> dict[str, int]:
    total_piles = len(piles)
    completed_piles = 0
    pending_qc = 0
    for pile in piles:
        matrix = _as_dict(pile.get("state_matrix"))
        pending_qc += _to_int(matrix.get("pending"), 0)
        stage = _to_text(pile.get("lifecycle_stage")).strip().lower()
        if stage in {"completed", "approved", "archived", "done"}:
            completed_piles += 1
            continue
        total_qc = _to_int(matrix.get("total_qc_tables"), 0)
        generated = _to_int(matrix.get("generated"), 0)
        signed = _to_int(matrix.get("signed"), 0)
        pending = _to_int(matrix.get("pending"), max(total_qc - generated, 0))
        if total_qc > 0 and pending <= 0 and signed >= max(generated, 0):
            completed_piles += 1
    return {"total_piles": total_piles, "completed_piles": completed_piles, "pending_qc": max(pending_qc, 0)}


def _bridge_state_matrix_from_sub_items(sub_items: list[dict[str, Any]]) -> dict[str, int]:
    pile_count = sum(1 for item in sub_items if _is_pile_like(item))
    return {"total_piles": pile_count, "completed_piles": 0, "pending_qc": 0}


def _uniq_text_list(items: list[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _to_text(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _stable_sub_item_key(item: dict[str, Any]) -> str:
    for key in ("pile_uri", "component_uri", "boq_item_uri", "boq_code"):
        token = _to_text(item.get(key)).strip()
        if token:
            return f"{key}:{token}"
    return f"sha:{_sha16(repr(sorted(item.items())))}"


def _normalize_sub_item(item: dict[str, Any], *, bridge_uri: str) -> dict[str, Any]:
    data = dict(item)
    component_uri = _to_text(data.get("component_uri")).strip()
    pile_uri = _to_text(data.get("pile_uri")).strip()
    component_type = _to_text(data.get("component_type")).strip().lower()
    pile_id = _to_text(data.get("pile_id")).strip()
    if not pile_uri and component_type == "pile" and component_uri:
        pile_uri = component_uri
    if not pile_id and pile_uri:
        pile_id = _tail_token(pile_uri)
    if not pile_id and component_type == "pile" and component_uri:
        pile_id = _tail_token(component_uri)
    if component_type == "pile" and pile_id and not pile_uri:
        pile_uri = _pile_uri(bridge_uri, pile_id)
    data["component_uri"] = component_uri
    data["pile_uri"] = pile_uri
    data["pile_id"] = _normalize_pile_token(pile_id) if pile_id else ""
    data["component_type"] = component_type or ("pile" if _is_pile_like(data) else "")
    return data


@dataclass(slots=True)
class BridgeEntity:
    bridge_id: str
    bridge_name: str
    project_uri: str
    parent_section: str
    boq_chapter: str
    bridge_slug: str
    bridge_uri: str
    sub_items: list[dict[str, Any]] = field(default_factory=list)
    total_piles: int = 0
    state_matrix: dict[str, int] = field(default_factory=dict)
    version: int = 1
    updated_at: str = ""


@dataclass(slots=True)
class PileEntity:
    pile_uri: str
    pile_id: str
    pile_type: str
    length_m: float
    bridge_uri: str
    bridge_name: str
    bridge_slug: str
    project_uri: str
    boq_item_uris: list[str] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    qc_report_uris: list[str] = field(default_factory=list)
    state_matrix: dict[str, int] = field(default_factory=dict)
    lifecycle_stage: str = "draft"
    version: int = 1
    updated_at: str = ""


def _entity_state(entity: BridgeEntity, *, action: str) -> dict[str, Any]:
    payload = asdict(entity)
    payload.update({"entity_type": "bridge_entity", "action": action})
    return payload


def _pile_state(entity: PileEntity, *, action: str) -> dict[str, Any]:
    payload = asdict(entity)
    payload.update({"entity_type": "pile_entity", "component_type": "pile", "action": action})
    return payload


def _create_proof(*, sb: Any, commit: bool, proof_id: str, owner_uri: str, project_uri: str, proof_type: str, result: str, segment_uri: str, norm_uri: str, state_data: dict[str, Any]) -> dict[str, Any]:
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
        raise HTTPException(502, f"failed to query bridge/pile entities: {exc}") from exc


def _latest_bridge_entities(*, sb: Any, project_uri: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in _fetch_node_rows(sb=sb, project_uri=project_uri):
        sd = _as_dict(row.get("state_data"))
        if _to_text(sd.get("entity_type")).strip() != "bridge_entity":
            continue
        slug = _to_text(sd.get("bridge_slug")).strip()
        if slug:
            latest[slug] = sd
    return latest


def _latest_pile_entities(*, sb: Any, project_uri: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in _fetch_node_rows(sb=sb, project_uri=project_uri):
        sd = _as_dict(row.get("state_data"))
        if _to_text(sd.get("entity_type")).strip() != "pile_entity":
            continue
        pile_uri = _to_text(sd.get("pile_uri")).strip()
        if pile_uri:
            latest[pile_uri] = sd
    return latest


def _find_bridge_entity_by_name(*, bridge_entities: dict[str, dict[str, Any]], bridge_name: str) -> dict[str, Any] | None:
    normalized_name = _to_text(bridge_name).strip().lower()
    if not normalized_name:
        return None
    for entity in bridge_entities.values():
        if _to_text(entity.get("bridge_name")).strip().lower() == normalized_name:
            return entity
    return None

def _sync_bridge_aggregate_from_piles(*, sb: Any, project_uri: str, bridge_uri: str, bridge_slug: str, bridge_name: str, owner_uri: str, commit: bool, source_action: str, candidate_piles: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    all_piles = _latest_pile_entities(sb=sb, project_uri=project_uri)
    bridge_piles = [
        dict(sd)
        for sd in all_piles.values()
        if _to_text(sd.get("bridge_uri")).strip().rstrip("/") == bridge_uri.rstrip("/")
    ]
    for pile in candidate_piles or []:
        if not isinstance(pile, dict):
            continue
        if _to_text(pile.get("bridge_uri")).strip().rstrip("/") != bridge_uri.rstrip("/"):
            continue
        pile_uri = _to_text(pile.get("pile_uri")).strip()
        replaced = False
        for idx, existed in enumerate(bridge_piles):
            if _to_text(existed.get("pile_uri")).strip() == pile_uri:
                bridge_piles[idx] = pile
                replaced = True
                break
        if not replaced:
            bridge_piles.append(pile)

    state_matrix = _bridge_state_matrix_from_piles(bridge_piles)
    bridge_entities = _latest_bridge_entities(sb=sb, project_uri=project_uri)
    latest_bridge = bridge_entities.get(bridge_slug) or _find_bridge_entity_by_name(bridge_entities=bridge_entities, bridge_name=bridge_name)

    bridge = BridgeEntity(
        bridge_id=_to_text(_as_dict(latest_bridge).get("bridge_id")).strip() or f"BRG-{_sha16(f'{project_uri}:{bridge_slug}').upper()}",
        bridge_name=_to_text(bridge_name).strip() or _to_text(_as_dict(latest_bridge).get("bridge_name")).strip() or bridge_slug,
        project_uri=project_uri,
        parent_section=_to_text(_as_dict(latest_bridge).get("parent_section")).strip(),
        boq_chapter=_to_text(_as_dict(latest_bridge).get("boq_chapter")).strip() or "400",
        bridge_slug=bridge_slug,
        bridge_uri=bridge_uri,
        sub_items=[item for item in _as_list(_as_dict(latest_bridge).get("sub_items")) if isinstance(item, dict)],
        total_piles=_to_int(state_matrix.get("total_piles"), 0),
        state_matrix=state_matrix,
        version=max(_to_int(_as_dict(latest_bridge).get("version"), 0) + 1, 1),
        updated_at=datetime.now(UTC).isoformat(),
    )
    state = _entity_state(bridge, action="pile_aggregate_sync")
    proof = _create_proof(
        sb=sb,
        commit=bool(commit),
        proof_id=f"GP-BRIDGE-AGG-{_sha16(f'{bridge_uri}:{bridge.version}:{source_action}').upper()}",
        owner_uri=owner_uri,
        project_uri=project_uri,
        proof_type="node",
        result="PASS",
        segment_uri=bridge_uri,
        norm_uri="v://norm/NormPeg/BridgeEntity/1.0",
        state_data={"proof_kind": "bridge_pile_aggregate", "source_action": source_action, "bridge_entity": state},
    )
    return {"bridge_uri": bridge_uri, "bridge_entity": state, "bridge_aggregate_proof": proof}


def _require_project_uri(project_uri: str) -> str:
    uri = _to_text(project_uri).strip().rstrip("/")
    if not uri:
        raise HTTPException(400, "project_uri is required")
    return uri


def _require_bridge_name(bridge_name: str) -> str:
    name = _to_text(bridge_name).strip()
    if not name:
        raise HTTPException(400, "bridge_name is required")
    return name


def _resolve_owner_uri(*, project_uri: str, owner_uri: str) -> str:
    owner = _to_text(owner_uri).strip()
    return owner or f"{project_uri.rstrip('/')}/role/system/"


def _resolve_bridge_seed(*, sb: Any, project_uri: str, bridge_name: str, parent_section: str, boq_chapter: str) -> dict[str, Any]:
    slug = _normalize_bridge_slug(bridge_name)
    uri = _bridge_uri(project_uri, slug)
    latest = _latest_bridge_entities(sb=sb, project_uri=project_uri)
    existed = latest.get(slug) or _find_bridge_entity_by_name(bridge_entities=latest, bridge_name=bridge_name) or {}
    return {
        "bridge_slug": slug,
        "bridge_uri": _to_text(existed.get("bridge_uri")).strip() or uri,
        "bridge_name": _to_text(existed.get("bridge_name")).strip() or bridge_name,
        "bridge_id": _to_text(existed.get("bridge_id")).strip() or f"BRG-{_sha16(f'{project_uri}:{slug}').upper()}",
        "parent_section": _to_text(existed.get("parent_section")).strip() or _to_text(parent_section).strip(),
        "boq_chapter": _to_text(existed.get("boq_chapter")).strip() or _to_text(boq_chapter).strip() or "400",
        "sub_items": [item for item in _as_list(existed.get("sub_items")) if isinstance(item, dict)],
        "version": _to_int(existed.get("version"), 0),
    }


def _merge_sub_items(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    index: dict[str, int] = {}
    for item in existing + incoming:
        if not isinstance(item, dict):
            continue
        key = _stable_sub_item_key(item)
        if key in index:
            merged[index[key]].update(item)
            continue
        index[key] = len(merged)
        merged.append(dict(item))
    return merged


def _candidate_pile_from_sub_item(item: dict[str, Any], *, bridge_seed: dict[str, Any], project_uri: str) -> dict[str, Any] | None:
    normalized = _normalize_sub_item(item, bridge_uri=_to_text(bridge_seed.get("bridge_uri")).strip())
    if not _is_pile_like(normalized):
        return None
    pile_id = _to_text(normalized.get("pile_id")).strip() or _tail_token(_to_text(normalized.get("pile_uri")).strip())
    if not pile_id:
        return None
    pile_uri = _to_text(normalized.get("pile_uri")).strip() or _pile_uri(_to_text(bridge_seed.get("bridge_uri")).strip(), pile_id)
    return {
        "pile_uri": pile_uri,
        "pile_id": _normalize_pile_token(pile_id),
        "pile_type": _to_text(normalized.get("pile_type")).strip() or "pile",
        "length_m": _to_float(normalized.get("length_m"), 0.0),
        "bridge_uri": _to_text(bridge_seed.get("bridge_uri")).strip(),
        "bridge_name": _to_text(bridge_seed.get("bridge_name")).strip(),
        "bridge_slug": _to_text(bridge_seed.get("bridge_slug")).strip(),
        "project_uri": project_uri,
        "boq_item_uris": _uniq_text_list([normalized.get("boq_item_uri")]),
        "materials": _uniq_text_list(_as_list(normalized.get("materials"))),
        "qc_report_uris": _uniq_text_list(_as_list(normalized.get("qc_report_uris"))),
        "state_matrix": _normalize_pile_state_matrix({}, _as_dict(normalized.get("state_matrix"))),
        "lifecycle_stage": "draft",
    }


def _upsert_pile_entity(*, sb: Any, project_uri: str, owner_uri: str, payload: dict[str, Any], commit: bool, action: str) -> tuple[dict[str, Any], dict[str, Any]]:
    latest = _latest_pile_entities(sb=sb, project_uri=project_uri).get(_to_text(payload.get("pile_uri")).strip(), {})

    matrix = _normalize_pile_state_matrix(_as_dict(latest).get("state_matrix"), _as_dict(payload.get("state_matrix")))
    lifecycle = _derive_lifecycle_stage(
        total=_to_int(matrix.get("total_qc_tables"), 0),
        generated=_to_int(matrix.get("generated"), 0),
        signed=_to_int(matrix.get("signed"), 0),
        pending=_to_int(matrix.get("pending"), 0),
        override=_to_text(payload.get("lifecycle_stage")).strip() or _to_text(_as_dict(latest).get("lifecycle_stage")).strip(),
    )

    entity = PileEntity(
        pile_uri=_to_text(payload.get("pile_uri")).strip(),
        pile_id=_normalize_pile_token(_to_text(payload.get("pile_id")).strip() or _tail_token(_to_text(payload.get("pile_uri")).strip())),
        pile_type=_to_text(payload.get("pile_type")).strip() or _to_text(_as_dict(latest).get("pile_type")).strip() or "pile",
        length_m=_to_float(payload.get("length_m"), _to_float(_as_dict(latest).get("length_m"), 0.0)),
        bridge_uri=_to_text(payload.get("bridge_uri")).strip() or _to_text(_as_dict(latest).get("bridge_uri")).strip(),
        bridge_name=_to_text(payload.get("bridge_name")).strip() or _to_text(_as_dict(latest).get("bridge_name")).strip(),
        bridge_slug=_to_text(payload.get("bridge_slug")).strip() or _to_text(_as_dict(latest).get("bridge_slug")).strip(),
        project_uri=project_uri,
        boq_item_uris=_uniq_text_list(_as_list(_as_dict(latest).get("boq_item_uris")) + _as_list(payload.get("boq_item_uris"))),
        materials=_uniq_text_list(_as_list(_as_dict(latest).get("materials")) + _as_list(payload.get("materials"))),
        qc_report_uris=_uniq_text_list(_as_list(_as_dict(latest).get("qc_report_uris")) + _as_list(payload.get("qc_report_uris"))),
        state_matrix=matrix,
        lifecycle_stage=lifecycle,
        version=max(_to_int(_as_dict(latest).get("version"), 0) + 1, 1),
        updated_at=datetime.now(UTC).isoformat(),
    )
    state = _pile_state(entity, action=action)
    proof = _create_proof(
        sb=sb,
        commit=bool(commit),
        proof_id=f"GP-PILE-{_sha16(f'{entity.pile_uri}:{entity.version}:{action}').upper()}",
        owner_uri=owner_uri,
        project_uri=project_uri,
        proof_type="node",
        result="PASS",
        segment_uri=entity.pile_uri,
        norm_uri="v://norm/NormPeg/PileEntity/1.0",
        state_data={"proof_kind": "pile_mapping" if action == "pile_mapping" else "pile_state_update", "pile_entity": state},
    )
    return state, proof

def create_bridge_entity(*, sb: Any, project_uri: str, bridge_name: str, parent_section: str = "", boq_chapter: str = "400", owner_uri: str = "", commit: bool = False) -> dict[str, Any]:
    project_uri = _require_project_uri(project_uri)
    bridge_name = _require_bridge_name(bridge_name)
    owner_uri = _resolve_owner_uri(project_uri=project_uri, owner_uri=owner_uri)

    seed = _resolve_bridge_seed(sb=sb, project_uri=project_uri, bridge_name=bridge_name, parent_section=parent_section, boq_chapter=boq_chapter)
    bridge_piles = [
        sd
        for sd in _latest_pile_entities(sb=sb, project_uri=project_uri).values()
        if _to_text(sd.get("bridge_uri")).strip().rstrip("/") == _to_text(seed.get("bridge_uri")).strip().rstrip("/")
    ]
    matrix = _bridge_state_matrix_from_piles(bridge_piles) if bridge_piles else _bridge_state_matrix_from_sub_items(seed["sub_items"])

    entity = BridgeEntity(
        bridge_id=_to_text(seed.get("bridge_id")).strip(),
        bridge_name=_to_text(seed.get("bridge_name")).strip(),
        project_uri=project_uri,
        parent_section=_to_text(seed.get("parent_section")).strip(),
        boq_chapter=_to_text(seed.get("boq_chapter")).strip() or "400",
        bridge_slug=_to_text(seed.get("bridge_slug")).strip(),
        bridge_uri=_to_text(seed.get("bridge_uri")).strip(),
        sub_items=[item for item in seed["sub_items"] if isinstance(item, dict)],
        total_piles=_to_int(matrix.get("total_piles"), 0),
        state_matrix=matrix,
        version=max(_to_int(seed.get("version"), 0) + 1, 1),
        updated_at=datetime.now(UTC).isoformat(),
    )
    state = _entity_state(entity, action="bridge_mapping")
    mapping_proof = _create_proof(
        sb=sb,
        commit=bool(commit),
        proof_id=f"GP-BRIDGE-{_sha16(f'{entity.bridge_uri}:{entity.version}:create').upper()}",
        owner_uri=owner_uri,
        project_uri=project_uri,
        proof_type="node",
        result="PASS",
        segment_uri=entity.bridge_uri,
        norm_uri="v://norm/NormPeg/BridgeEntity/1.0",
        state_data={"proof_kind": "bridge_mapping", "bridge_entity": state},
    )
    return {"ok": True, "project_uri": project_uri, "bridge_uri": entity.bridge_uri, "entity": state, "proofs": {"mapping_proof": mapping_proof}}


def bind_bridge_sub_items(*, sb: Any, project_uri: str, bridge_name: str, sub_items: list[dict[str, Any]] | None = None, parent_section: str = "", boq_chapter: str = "400", owner_uri: str = "", commit: bool = False) -> dict[str, Any]:
    project_uri = _require_project_uri(project_uri)
    bridge_name = _require_bridge_name(bridge_name)
    owner_uri = _resolve_owner_uri(project_uri=project_uri, owner_uri=owner_uri)

    seed = _resolve_bridge_seed(sb=sb, project_uri=project_uri, bridge_name=bridge_name, parent_section=parent_section, boq_chapter=boq_chapter)
    incoming = [_normalize_sub_item(item, bridge_uri=_to_text(seed.get("bridge_uri")).strip()) for item in _as_list(sub_items) if isinstance(item, dict)]
    merged_sub_items = _merge_sub_items(seed["sub_items"], incoming)

    pile_proofs: list[dict[str, Any]] = []
    candidate_piles: list[dict[str, Any]] = []
    for item in merged_sub_items:
        candidate = _candidate_pile_from_sub_item(item, bridge_seed=seed, project_uri=project_uri)
        if not isinstance(candidate, dict):
            continue
        pile_state, pile_proof = _upsert_pile_entity(
            sb=sb,
            project_uri=project_uri,
            owner_uri=owner_uri,
            payload=candidate,
            commit=bool(commit),
            action="pile_mapping",
        )
        candidate_piles.append(pile_state)
        pile_proofs.append(pile_proof)

    if candidate_piles:
        aggregate = _sync_bridge_aggregate_from_piles(
            sb=sb,
            project_uri=project_uri,
            bridge_uri=_to_text(seed.get("bridge_uri")).strip(),
            bridge_slug=_to_text(seed.get("bridge_slug")).strip(),
            bridge_name=_to_text(seed.get("bridge_name")).strip(),
            owner_uri=owner_uri,
            commit=bool(commit),
            source_action="bind_bridge_sub_items",
            candidate_piles=candidate_piles,
        )
        bridge_state = _as_dict(aggregate.get("bridge_entity"))
        state_matrix = _as_dict(bridge_state.get("state_matrix"))
    else:
        state_matrix = _bridge_state_matrix_from_sub_items(merged_sub_items)
        bridge_entity = BridgeEntity(
            bridge_id=_to_text(seed.get("bridge_id")).strip(),
            bridge_name=_to_text(seed.get("bridge_name")).strip(),
            project_uri=project_uri,
            parent_section=_to_text(seed.get("parent_section")).strip(),
            boq_chapter=_to_text(seed.get("boq_chapter")).strip() or "400",
            bridge_slug=_to_text(seed.get("bridge_slug")).strip(),
            bridge_uri=_to_text(seed.get("bridge_uri")).strip(),
            sub_items=merged_sub_items,
            total_piles=_to_int(state_matrix.get("total_piles"), 0),
            state_matrix=state_matrix,
            version=max(_to_int(seed.get("version"), 0) + 1, 1),
            updated_at=datetime.now(UTC).isoformat(),
        )
        bridge_state = _entity_state(bridge_entity, action="bridge_binding")
        aggregate = {"bridge_aggregate_proof": None}

    bridge_state["sub_items"] = merged_sub_items
    bridge_state["total_piles"] = _to_int(state_matrix.get("total_piles"), _to_int(bridge_state.get("total_piles"), 0))
    bridge_state["state_matrix"] = {
        "total_piles": _to_int(state_matrix.get("total_piles"), 0),
        "completed_piles": _to_int(state_matrix.get("completed_piles"), 0),
        "pending_qc": _to_int(state_matrix.get("pending_qc"), 0),
    }

    binding_proof = _create_proof(
        sb=sb,
        commit=bool(commit),
        proof_id=f"GP-BRIDGE-BIND-{_sha16(f'{bridge_state.get('bridge_uri')}:{len(merged_sub_items)}').upper()}",
        owner_uri=owner_uri,
        project_uri=project_uri,
        proof_type="node",
        result="PASS",
        segment_uri=_to_text(bridge_state.get("bridge_uri")).strip(),
        norm_uri="v://norm/NormPeg/BridgeEntity/1.0",
        state_data={"proof_kind": "bridge_binding", "bridge_entity": bridge_state},
    )
    return {
        "ok": True,
        "project_uri": project_uri,
        "bridge_uri": _to_text(bridge_state.get("bridge_uri")).strip(),
        "entity": bridge_state,
        "proofs": {
            "binding_proof": binding_proof,
            "pile_mapping_proofs": pile_proofs,
            "bridge_aggregate_proof": aggregate.get("bridge_aggregate_proof"),
        },
    }


def create_pile_entity(*, sb: Any, project_uri: str, bridge_name: str, pile_id: str, pile_type: str = "", length_m: float = 0.0, boq_item_uris: list[str] | None = None, materials: list[str] | None = None, qc_report_uris: list[str] | None = None, state_matrix: dict[str, Any] | None = None, owner_uri: str = "", commit: bool = False) -> dict[str, Any]:
    project_uri = _require_project_uri(project_uri)
    bridge_name = _require_bridge_name(bridge_name)
    pile_token = _normalize_pile_token(pile_id)
    if not pile_token:
        raise HTTPException(400, "pile_id is required")
    owner_uri = _resolve_owner_uri(project_uri=project_uri, owner_uri=owner_uri)

    seed = _resolve_bridge_seed(sb=sb, project_uri=project_uri, bridge_name=bridge_name, parent_section="", boq_chapter="400")
    payload = {
        "pile_uri": _pile_uri(_to_text(seed.get("bridge_uri")).strip(), pile_token),
        "pile_id": pile_token,
        "pile_type": _to_text(pile_type).strip() or "pile",
        "length_m": _to_float(length_m, 0.0),
        "bridge_uri": _to_text(seed.get("bridge_uri")).strip(),
        "bridge_name": _to_text(seed.get("bridge_name")).strip(),
        "bridge_slug": _to_text(seed.get("bridge_slug")).strip(),
        "project_uri": project_uri,
        "boq_item_uris": _uniq_text_list(_as_list(boq_item_uris)),
        "materials": _uniq_text_list(_as_list(materials)),
        "qc_report_uris": _uniq_text_list(_as_list(qc_report_uris)),
        "state_matrix": _normalize_pile_state_matrix({}, _as_dict(state_matrix)),
        "lifecycle_stage": "",
    }
    pile_state, mapping_proof = _upsert_pile_entity(sb=sb, project_uri=project_uri, owner_uri=owner_uri, payload=payload, commit=bool(commit), action="pile_mapping")
    aggregate = _sync_bridge_aggregate_from_piles(
        sb=sb,
        project_uri=project_uri,
        bridge_uri=_to_text(seed.get("bridge_uri")).strip(),
        bridge_slug=_to_text(seed.get("bridge_slug")).strip(),
        bridge_name=_to_text(seed.get("bridge_name")).strip(),
        owner_uri=owner_uri,
        commit=bool(commit),
        source_action="create_pile_entity",
        candidate_piles=[pile_state],
    )
    return {
        "ok": True,
        "project_uri": project_uri,
        "bridge_uri": _to_text(seed.get("bridge_uri")).strip(),
        "pile_uri": _to_text(pile_state.get("pile_uri")).strip(),
        "pile_entity": pile_state,
        "bridge_entity": aggregate.get("bridge_entity"),
        "proofs": {"mapping_proof": mapping_proof, "bridge_aggregate_proof": aggregate.get("bridge_aggregate_proof")},
    }


def update_pile_state_matrix(*, sb: Any, project_uri: str, bridge_name: str, pile_id: str, updates: dict[str, Any], owner_uri: str = "", commit: bool = False) -> dict[str, Any]:
    project_uri = _require_project_uri(project_uri)
    bridge_name = _require_bridge_name(bridge_name)
    pile_token = _normalize_pile_token(pile_id)
    if not pile_token:
        raise HTTPException(400, "pile_id is required")
    owner_uri = _resolve_owner_uri(project_uri=project_uri, owner_uri=owner_uri)

    seed = _resolve_bridge_seed(sb=sb, project_uri=project_uri, bridge_name=bridge_name, parent_section="", boq_chapter="400")
    pile_uri = _pile_uri(_to_text(seed.get("bridge_uri")).strip(), pile_token)
    latest = _latest_pile_entities(sb=sb, project_uri=project_uri).get(pile_uri)
    if latest is None and sb is not None:
        raise HTTPException(404, f"pile entity not found: {pile_uri}")

    payload = {
        "pile_uri": pile_uri,
        "pile_id": pile_token,
        "pile_type": _to_text(_as_dict(latest).get("pile_type")).strip() or "pile",
        "length_m": _to_float(_as_dict(latest).get("length_m"), 0.0),
        "bridge_uri": _to_text(seed.get("bridge_uri")).strip(),
        "bridge_name": _to_text(seed.get("bridge_name")).strip(),
        "bridge_slug": _to_text(seed.get("bridge_slug")).strip(),
        "project_uri": project_uri,
        "boq_item_uris": _as_list(_as_dict(latest).get("boq_item_uris")),
        "materials": _as_list(_as_dict(latest).get("materials")),
        "qc_report_uris": _uniq_text_list(_as_list(_as_dict(latest).get("qc_report_uris")) + _as_list(_as_dict(updates).get("qc_report_uris"))),
        "state_matrix": _normalize_pile_state_matrix(_as_dict(_as_dict(latest).get("state_matrix")), _as_dict(updates)),
        "lifecycle_stage": _to_text(_as_dict(updates).get("lifecycle_stage")).strip(),
    }
    pile_state, state_proof = _upsert_pile_entity(sb=sb, project_uri=project_uri, owner_uri=owner_uri, payload=payload, commit=bool(commit), action="pile_state_update")
    aggregate = _sync_bridge_aggregate_from_piles(
        sb=sb,
        project_uri=project_uri,
        bridge_uri=_to_text(seed.get("bridge_uri")).strip(),
        bridge_slug=_to_text(seed.get("bridge_slug")).strip(),
        bridge_name=_to_text(seed.get("bridge_name")).strip(),
        owner_uri=owner_uri,
        commit=bool(commit),
        source_action="update_pile_state_matrix",
        candidate_piles=[pile_state],
    )
    return {
        "ok": True,
        "project_uri": project_uri,
        "bridge_uri": _to_text(seed.get("bridge_uri")).strip(),
        "pile_uri": pile_uri,
        "pile_entity": pile_state,
        "bridge_entity": aggregate.get("bridge_entity"),
        "proofs": {"state_update_proof": state_proof, "bridge_aggregate_proof": aggregate.get("bridge_aggregate_proof")},
    }


def get_pile_entity_detail(*, sb: Any, project_uri: str, bridge_name: str, pile_id: str) -> dict[str, Any]:
    project_uri = _require_project_uri(project_uri)
    bridge_name = _require_bridge_name(bridge_name)
    pile_token = _normalize_pile_token(pile_id)
    if not pile_token:
        raise HTTPException(400, "pile_id is required")

    seed = _resolve_bridge_seed(sb=sb, project_uri=project_uri, bridge_name=bridge_name, parent_section="", boq_chapter="400")
    pile_uri = _pile_uri(_to_text(seed.get("bridge_uri")).strip(), pile_token)
    latest = _latest_pile_entities(sb=sb, project_uri=project_uri).get(pile_uri)
    if latest is None:
        raise HTTPException(404, f"pile entity not found: {pile_uri}")
    return {"ok": True, "project_uri": project_uri, "bridge_uri": _to_text(seed.get("bridge_uri")).strip(), "pile_uri": pile_uri, "pile_entity": dict(latest)}


def get_bridge_pile_detail(*, sb: Any, project_uri: str, bridge_name: str) -> dict[str, Any]:
    project_uri = _require_project_uri(project_uri)
    bridge_name = _require_bridge_name(bridge_name)

    bridge_entities = _latest_bridge_entities(sb=sb, project_uri=project_uri)
    bridge = bridge_entities.get(_normalize_bridge_slug(bridge_name)) or _find_bridge_entity_by_name(bridge_entities=bridge_entities, bridge_name=bridge_name)
    seed = _resolve_bridge_seed(sb=sb, project_uri=project_uri, bridge_name=bridge_name, parent_section="", boq_chapter="400")
    bridge_uri = _to_text(seed.get("bridge_uri")).strip()

    pile_entities = [
        dict(sd)
        for sd in _latest_pile_entities(sb=sb, project_uri=project_uri).values()
        if _to_text(sd.get("bridge_uri")).strip().rstrip("/") == bridge_uri.rstrip("/")
    ]

    if pile_entities:
        pile_items = [
            {
                "pile_uri": _to_text(item.get("pile_uri")).strip(),
                "pile_id": _to_text(item.get("pile_id")).strip(),
                "pile_type": _to_text(item.get("pile_type")).strip(),
                "length_m": _to_float(item.get("length_m"), 0.0),
                "state_matrix": _as_dict(item.get("state_matrix")),
                "lifecycle_stage": _to_text(item.get("lifecycle_stage")).strip(),
                "boq_item_uris": _as_list(item.get("boq_item_uris")),
                "materials": _as_list(item.get("materials")),
                "qc_report_uris": _as_list(item.get("qc_report_uris")),
            }
            for item in pile_entities
        ]
        matrix = _bridge_state_matrix_from_piles(pile_entities)
    else:
        sub_items = [item for item in _as_list(_as_dict(bridge).get("sub_items")) if isinstance(item, dict)]
        pile_items = [item for item in sub_items if _is_pile_like(item)]
        matrix = _bridge_state_matrix_from_sub_items(sub_items)

    if not bridge and not pile_items:
        raise HTTPException(404, f"bridge entity not found: {bridge_name}")

    bridge_state = {
        "bridge_slug": _to_text(_as_dict(bridge).get("bridge_slug")).strip() or _to_text(seed.get("bridge_slug")).strip(),
        "bridge_name": _to_text(_as_dict(bridge).get("bridge_name")).strip() or _to_text(seed.get("bridge_name")).strip(),
        "bridge_uri": bridge_uri,
        "parent_section": _to_text(_as_dict(bridge).get("parent_section")).strip() or _to_text(seed.get("parent_section")).strip(),
        "boq_chapter": _to_text(_as_dict(bridge).get("boq_chapter")).strip() or _to_text(seed.get("boq_chapter")).strip(),
        "version": _to_int(_as_dict(bridge).get("version"), 0),
        "state_matrix": {
            "total_piles": _to_int(matrix.get("total_piles"), 0),
            "completed_piles": _to_int(matrix.get("completed_piles"), 0),
            "pending_qc": _to_int(matrix.get("pending_qc"), 0),
        },
    }

    return {
        "ok": True,
        "project_uri": project_uri,
        "bridge_uri": bridge_uri,
        "bridge_name": bridge_state["bridge_name"],
        "total_piles": _to_int(matrix.get("total_piles"), _to_int(_as_dict(bridge).get("total_piles"), len(pile_items))),
        "pile_items": pile_items,
        "entity": bridge_state,
    }


def get_full_line_pile_summary(*, sb: Any, project_uri: str) -> dict[str, Any]:
    project_uri = _require_project_uri(project_uri)
    bridge_entities = _latest_bridge_entities(sb=sb, project_uri=project_uri)
    pile_entities = _latest_pile_entities(sb=sb, project_uri=project_uri)

    piles_by_bridge: dict[str, list[dict[str, Any]]] = {}
    for pile in pile_entities.values():
        bridge_uri = _to_text(pile.get("bridge_uri")).strip().rstrip("/")
        if bridge_uri:
            piles_by_bridge.setdefault(bridge_uri, []).append(dict(pile))

    bridges: list[dict[str, Any]] = []
    touched: set[str] = set()
    for bridge in bridge_entities.values():
        bridge_uri = _to_text(bridge.get("bridge_uri")).strip().rstrip("/") or _bridge_uri(project_uri, _to_text(bridge.get("bridge_slug")).strip())
        pile_list = piles_by_bridge.get(bridge_uri, [])
        if pile_list:
            matrix = _bridge_state_matrix_from_piles(pile_list)
            total_piles = _to_int(matrix.get("total_piles"), 0)
        else:
            sub_items = [item for item in _as_list(bridge.get("sub_items")) if isinstance(item, dict)]
            matrix = _as_dict(bridge.get("state_matrix")) or _bridge_state_matrix_from_sub_items(sub_items)
            total_piles = _to_int(matrix.get("total_piles"), _to_int(bridge.get("total_piles"), 0))
        bridges.append(
            {
                "bridge_name": _to_text(bridge.get("bridge_name")).strip(),
                "bridge_slug": _to_text(bridge.get("bridge_slug")).strip(),
                "bridge_uri": bridge_uri,
                "total_piles": total_piles,
                "completed_piles": _to_int(matrix.get("completed_piles"), 0),
                "pending_qc": _to_int(matrix.get("pending_qc"), 0),
            }
        )
        touched.add(bridge_uri)

    for bridge_uri, pile_list in piles_by_bridge.items():
        if bridge_uri in touched:
            continue
        matrix = _bridge_state_matrix_from_piles(pile_list)
        bridges.append(
            {
                "bridge_name": _tail_token(bridge_uri),
                "bridge_slug": _tail_token(bridge_uri),
                "bridge_uri": bridge_uri,
                "total_piles": _to_int(matrix.get("total_piles"), 0),
                "completed_piles": _to_int(matrix.get("completed_piles"), 0),
                "pending_qc": _to_int(matrix.get("pending_qc"), 0),
            }
        )

    return {
        "ok": True,
        "project_uri": project_uri,
        "full_line_uri": f"{project_uri.rstrip('/')}/full-line",
        "bridge_count": len(bridges),
        "pile_total": sum(_to_int(item.get("total_piles"), 0) for item in bridges),
        "bridges": bridges,
    }


__all__ = [
    "bind_bridge_sub_items",
    "create_bridge_entity",
    "create_pile_entity",
    "get_bridge_pile_detail",
    "get_full_line_pile_summary",
    "get_pile_entity_detail",
    "update_pile_state_matrix",
]

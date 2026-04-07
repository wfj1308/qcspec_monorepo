"""DocPeg SpecIR v1.1 canonical document structure helpers."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import re
from typing import Any

from services.api.core.docpeg import DTORole, Role

DOCPEG_SPECIR_V11_SCHEMA_URI = "v://normref.com/schema/docpeg-specir-v1.1"

_ALLOWED_STAGES = {"draft", "pending_review", "approved", "archived"}


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


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def _slug(value: Any) -> str:
    text = _to_text(value).strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff_-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "document"


def _sha256_json(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(_as_dict(out.get(key)), value)
        else:
            out[key] = value
    return out


def _normalize_doc_type_uri(doc_type: str) -> str:
    text = _to_text(doc_type).strip()
    if not text:
        return "v://normref.com/doc-type/general-document@v1"
    if text.startswith("v://"):
        return text
    return f"v://normref.com/doc-type/{_slug(text)}@v1"


def _normalize_trip_role(value: Any, default: str = "document.register") -> str:
    text = _to_text(value).strip().lower()
    return text or default


def _role_value(value: str | Role | None, default: Role = Role.PUBLIC) -> Role:
    try:
        return DTORole.normalize(value)
    except Exception:
        return default


def _default_dtorole_permissions() -> dict[str, list[str]]:
    return {
        "PUBLIC": ["can_view_summary"],
        "MARKET": ["can_view_summary"],
        "AI": ["can_view_qc_fields", "can_propose"],
        "SUPERVISOR": ["can_view_gate_results", "can_approve"],
        "OWNER": ["can_modify", "can_view_full_proof", "can_archive"],
        "REGULATOR": ["can_view_audit_summary", "can_view_result"],
    }


def build_docpeg_specir_v11(
    *,
    project_uri: str,
    node_uri: str,
    source_utxo_id: str,
    file_name: str,
    mime_type: str,
    storage_url: str,
    text_excerpt: str = "",
    ai_metadata: dict[str, Any] | None = None,
    custom_metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    lifecycle_stage: str = "",
    trigger_event: str = "",
    created_at: str = "",
    jurisdiction: str = "",
    proof_hash: str = "",
    trip_role: str = "",
    dtorole_context: str | Role | None = None,
    trip_context: dict[str, Any] | None = None,
    required_trip_roles: list[str] | None = None,
    dtorole_permissions: dict[str, Any] | None = None,
    dtorole_proof: dict[str, Any] | None = None,
    dtorole_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ai_meta = _as_dict(ai_metadata)
    custom = _as_dict(custom_metadata)
    doc_spec_override = _as_dict(custom.get("docpeg_specir_v1_1"))
    created = _to_text(created_at).strip() or _utc_iso()
    stage = _to_text(lifecycle_stage).strip().lower() or "draft"
    if stage not in _ALLOWED_STAGES:
        stage = "draft"
    role_ctx = _role_value(dtorole_context, default=Role.OWNER)
    normalized_trip_role = _normalize_trip_role(trip_role or trigger_event or custom.get("trip_role"))
    permissions = _default_dtorole_permissions()
    permissions = _deep_merge(permissions, _as_dict(dtorole_permissions))
    permissions = _deep_merge(permissions, _as_dict(custom.get("dtorole_permissions")))
    trip_ctx_payload = {
        "trip_role": normalized_trip_role,
        "executed_by": _to_text(_as_dict(trip_context).get("executed_by") or custom.get("executed_by")).strip(),
        "executed_at": _to_text(_as_dict(trip_context).get("executed_at") or created).strip(),
        "input": _as_dict(_as_dict(trip_context).get("input")),
        "output": _as_dict(_as_dict(trip_context).get("output")),
    }
    if not trip_ctx_payload["executed_by"]:
        trip_ctx_payload["executed_by"] = "v://executor/system/"

    doc_type_uri = _normalize_doc_type_uri(ai_meta.get("doc_type"))
    doc_id = _to_text(custom.get("doc_id")).strip() or f"DOC-{_sha256_json([project_uri, node_uri, file_name, created])[:16].upper()}"
    v_uri = _to_text(custom.get("v_uri")).strip() or f"{_to_text(node_uri).strip().rstrip('/')}/doc/{_slug(doc_id)}"

    norm_refs: list[str] = []
    for one in _as_list(custom.get("norm_refs")) + _as_list(ai_meta.get("norm_refs")):
        uri = _to_text(one).strip()
        if not uri:
            continue
        norm_refs.append(uri if uri.startswith("v://") else f"v://normref.com/{_slug(uri)}")
    if not norm_refs:
        norm_refs = ["v://norm/CoordOS/DocGovernance/1.0#document_register"]

    relations: list[dict[str, Any]] = []
    source_boq_uri = _to_text(custom.get("source_boq_item_uri")).strip()
    if source_boq_uri.startswith("v://"):
        relations.append({"type": "BOQItem", "uri": source_boq_uri})
    relations.append({"type": "ProofUTXO", "id": _to_text(source_utxo_id).strip()})
    for uri in _as_list(custom.get("relation_uris")):
        text = _to_text(uri).strip()
        if text.startswith("v://"):
            relations.append({"type": "Related", "uri": text})

    base: dict[str, Any] = {
        "schema_uri": DOCPEG_SPECIR_V11_SCHEMA_URI,
        "version": "v1.1",
        "header": {
            "doc_type": doc_type_uri,
            "doc_id": doc_id,
            "v_uri": v_uri,
            "version": "v1.1",
            "created_at": created,
            "project_ref": _to_text(project_uri).strip(),
            "jurisdiction": _to_text(jurisdiction).strip() or _to_text(custom.get("jurisdiction")).strip() or "CN-JTG",
            "trip_role": normalized_trip_role,
            "dtorole_context": role_ctx.value,
        },
        "gate": {
            "pre_conditions": _as_list(custom.get("pre_conditions")) or ["source_utxo_exists"],
            "entry_rules": _as_list(custom.get("entry_rules"))
            or [{"rule_id": "source_utxo_exists", "operator": "exists", "field": "source_utxo_id"}],
            "trigger_event": _to_text(trigger_event).strip() or "document.register",
            "norm_refs": norm_refs,
            "required_trip_roles": [
                _normalize_trip_role(x, default=normalized_trip_role)
                for x in (_as_list(required_trip_roles) or _as_list(custom.get("required_trip_roles")) or [normalized_trip_role])
                if _to_text(x).strip()
            ],
            "dtorole_permissions": permissions,
        },
        "body": {
            "basic": {
                "file_name": _to_text(file_name).strip(),
                "mime_type": _to_text(mime_type).strip(),
                "storage_url": _to_text(storage_url).strip(),
                "summary": _to_text(ai_meta.get("summary") or text_excerpt).strip()[:2000],
                "tags": [t for t in (_to_text(x).strip() for x in _as_list(tags)) if t],
            },
            "items": _as_list(custom.get("items")),
            "relations": relations,
            "trip_context": trip_ctx_payload,
        },
        "proof": {
            "signatures": _as_list(custom.get("signatures")),
            "timestamps": _as_list(custom.get("timestamps")) or [{"type": "created_at", "value": created}],
            "data_hash": "",
            "witness_logs": _as_list(custom.get("witness_logs")),
            "audit_trail": _as_list(custom.get("audit_trail"))
            or [{"action": "document.register", "at": created, "source_utxo_id": _to_text(source_utxo_id).strip()}],
            "proof_hash": _to_text(proof_hash).strip(),
            "trip_proof_hash": _to_text(custom.get("trip_proof_hash")).strip(),
            "dtorole_proof": _as_dict(custom.get("dtorole_proof")) or _as_dict(dtorole_proof),
        },
        "state": {
            "lifecycle_stage": stage,
            "valid_until": _to_text(custom.get("valid_until")).strip(),
            "retention_period": _to_text(custom.get("retention_period")).strip() or "P10Y",
            "access_level": _to_text(custom.get("access_level")).strip() or "project_internal",
            "next_action": _to_text(custom.get("next_action")).strip(),
            "state_matrix": _as_dict(custom.get("state_matrix")) or {"completed": 0, "pending": 1, "total": 1},
            "current_trip_role": normalized_trip_role,
            "dtorole_state": _as_dict(custom.get("dtorole_state")) or _as_dict(dtorole_state),
        },
    }
    out = _deep_merge(base, doc_spec_override) if doc_spec_override else base

    if not isinstance(out.get("header"), dict):
        out["header"] = base["header"]
    if not isinstance(out.get("gate"), dict):
        out["gate"] = base["gate"]
    if not isinstance(out.get("body"), dict):
        out["body"] = base["body"]
    if not isinstance(out.get("proof"), dict):
        out["proof"] = base["proof"]
    if not isinstance(out.get("state"), dict):
        out["state"] = base["state"]

    out["proof"]["data_hash"] = _sha256_json(out["body"])
    if not _to_text(out["proof"].get("proof_hash")).strip():
        out["proof"]["proof_hash"] = _sha256_json(
            {
                "header": out["header"],
                "gate": out["gate"],
                "body_hash": out["proof"]["data_hash"],
                "state": out["state"],
            }
        )
    if not _to_text(_as_dict(out.get("proof")).get("trip_proof_hash")).strip():
        out["proof"]["trip_proof_hash"] = _to_text(out["proof"].get("proof_hash")).strip()
    return out


def project_docpeg_specir_v11_for_role(
    *,
    spec: dict[str, Any],
    dto_role: str | Role | None,
) -> dict[str, Any]:
    role = _role_value(dto_role, default=Role.PUBLIC)
    src = _as_dict(spec)
    if not src:
        return {}
    out = json.loads(json.dumps(src, ensure_ascii=False, default=str))
    header = _as_dict(out.get("header"))
    gate = _as_dict(out.get("gate"))
    body = _as_dict(out.get("body"))
    proof = _as_dict(out.get("proof"))
    state = _as_dict(out.get("state"))

    header["dtorole_context"] = role.value
    out["header"] = header

    if role in {Role.PUBLIC, Role.MARKET}:
        out["gate"] = {
            "trigger_event": _to_text(gate.get("trigger_event")).strip(),
            "norm_refs": _as_list(gate.get("norm_refs")),
            "required_trip_roles": _as_list(gate.get("required_trip_roles")),
        }
        basic = _as_dict(body.get("basic"))
        out["body"] = {
            "basic": {
                "file_name": _to_text(basic.get("file_name")).strip(),
                "summary": _to_text(basic.get("summary")).strip(),
                "tags": _as_list(basic.get("tags")),
            },
            "trip_context": {
                "trip_role": _to_text(_as_dict(body.get("trip_context")).get("trip_role")).strip(),
                "executed_at": _to_text(_as_dict(body.get("trip_context")).get("executed_at")).strip(),
            },
        }
        role_proof = _as_dict(proof.get("dtorole_proof"))
        out["proof"] = {
            "trip_proof_hash": _to_text(proof.get("trip_proof_hash") or proof.get("proof_hash")).strip(),
            "proof_hash": _to_text(proof.get("proof_hash")).strip(),
            "dtorole_proof": role_proof.get(role.value) or role_proof.get("PUBLIC") or "",
        }
        role_state = _as_dict(state.get("dtorole_state"))
        out["state"] = {
            "lifecycle_stage": _to_text(state.get("lifecycle_stage")).strip(),
            "current_trip_role": _to_text(state.get("current_trip_role")).strip(),
            "dtorole_state": role_state.get(role.value) or role_state.get("PUBLIC") or _to_text(state.get("lifecycle_stage")).strip(),
        }
        return out

    if role in {Role.SUPERVISOR, Role.REGULATOR, Role.AI}:
        out["gate"] = {
            "pre_conditions": _as_list(gate.get("pre_conditions")),
            "entry_rules": _as_list(gate.get("entry_rules")),
            "trigger_event": _to_text(gate.get("trigger_event")).strip(),
            "norm_refs": _as_list(gate.get("norm_refs")),
            "required_trip_roles": _as_list(gate.get("required_trip_roles")),
            "dtorole_permissions": _as_dict(gate.get("dtorole_permissions")),
        }
        role_proof = _as_dict(proof.get("dtorole_proof"))
        proof["dtorole_proof"] = role_proof.get(role.value) or role_proof
        out["proof"] = proof
        role_state = _as_dict(state.get("dtorole_state"))
        state["dtorole_state"] = role_state.get(role.value) or role_state
        out["state"] = state
        return out

    return out


__all__ = [
    "DOCPEG_SPECIR_V11_SCHEMA_URI",
    "build_docpeg_specir_v11",
    "project_docpeg_specir_v11_for_role",
]

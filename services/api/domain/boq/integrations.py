"""BOQ-domain integration entry points."""

from __future__ import annotations

from services.api.domain.boq.runtime.audit_common import (
    as_dict,
    as_list,
    chain_root_hash,
    to_float,
    to_text,
)
from services.api.domain.boq.runtime.audit_engine import (
    get_item_sovereign_history,
    run_boq_audit_engine,
)
from services.api.domain.execution.runtime.did_reputation import build_did_reputation_summary, compute_did_reputation
from services.api.domain.proof.runtime.docpeg_proof_chain import (
    build_chain_fingerprints as docpeg_build_chain_fingerprints,
    get_proof_chain as docpeg_get_proof_chain,
)
from services.api.domain.verify.runtime.evidence_center import get_all_evidence_for_item
from services.api.domain.boq.runtime.gate_rule_editor import (
    generate_rules_via_ai,
    get_gate_editor_payload,
    import_from_norm_library,
    rollback_gate_rule,
    save_gate_rule_version,
)
from services.api.domain.execution.runtime.labpeg_frequency_remediation import get_frequency_dashboard
from services.api.domain.execution.runtime.phygital_sealing import build_sealing_trip
from services.api.domain.boq.runtime.specdict_gate import (
    get_spec_dict,
    resolve_dynamic_threshold,
    save_spec_dict,
)
from services.api.domain.verify.runtime.unit_merkle import build_unit_merkle_snapshot
from services.api.domain.verify.runtime.public_flow import get_public_verify_detail_flow

__all__ = [
    "as_dict",
    "as_list",
    "chain_root_hash",
    "to_float",
    "to_text",
    "get_item_sovereign_history",
    "run_boq_audit_engine",
    "get_all_evidence_for_item",
    "build_unit_merkle_snapshot",
    "build_did_reputation_summary",
    "compute_did_reputation",
    "docpeg_build_chain_fingerprints",
    "docpeg_get_proof_chain",
    "get_frequency_dashboard",
    "build_sealing_trip",
    "get_public_verify_detail_flow",
    "get_gate_editor_payload",
    "import_from_norm_library",
    "generate_rules_via_ai",
    "save_gate_rule_version",
    "rollback_gate_rule",
    "get_spec_dict",
    "save_spec_dict",
    "resolve_dynamic_threshold",
]

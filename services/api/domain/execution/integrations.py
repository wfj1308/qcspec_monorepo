"""Execution-domain integration entry points.

Centralizes external service imports so execution modules depend on a stable
local boundary instead of importing root-level services directly.
"""

from __future__ import annotations

from services.api.domain.boq.runtime.utxo import resolve_linked_gates
from services.api.domain.execution.runtime.did_gate import (
    resolve_required_credential,
    verify_credential,
)
from services.api.domain.execution.runtime.did_reputation import (
    build_did_reputation_summary,
    compute_did_reputation,
)
from services.api.domain.proof.runtime.docpeg_proof_chain import (
    build_dsp_zip_package,
    build_rebar_report_context,
    get_proof_chain,
    render_rebar_inspection_docx,
    render_rebar_inspection_pdf,
)
from services.api.domain.verify.runtime.evidence_center import get_all_evidence_for_item
from services.api.domain.execution.runtime.labpeg_frequency_remediation import (
    calc_inspection_frequency,
    close_remediation_trip,
    get_frequency_dashboard,
    open_remediation_trip,
    record_lab_test,
    remediation_reinspect,
    resolve_dual_pass_gate,
)
from services.api.core.norm.normpeg_engine import resolve_normpeg_eval
from services.api.domain.execution.runtime.phygital_sealing import build_sealing_trip
from services.api.domain.utxo.integrations import ProofUTXOEngine
from services.api.domain.execution.runtime.shadow_ledger import sync_to_mirrors
from services.api.domain.execution.runtime.sovereign_credit import calculate_sovereign_credit
from services.api.domain.boq.runtime.specdict_gate import (
    evaluate_with_threshold_pack,
    resolve_dynamic_threshold,
)
from services.api.domain.verify.runtime.service import get_project_name_by_id

__all__ = [
    "resolve_required_credential",
    "verify_credential",
    "compute_did_reputation",
    "build_did_reputation_summary",
    "record_lab_test",
    "calc_inspection_frequency",
    "get_frequency_dashboard",
    "open_remediation_trip",
    "remediation_reinspect",
    "close_remediation_trip",
    "resolve_dual_pass_gate",
    "ProofUTXOEngine",
    "sync_to_mirrors",
    "calculate_sovereign_credit",
    "resolve_normpeg_eval",
    "resolve_dynamic_threshold",
    "evaluate_with_threshold_pack",
    "get_proof_chain",
    "build_rebar_report_context",
    "render_rebar_inspection_docx",
    "render_rebar_inspection_pdf",
    "build_dsp_zip_package",
    "get_all_evidence_for_item",
    "build_sealing_trip",
    "get_project_name_by_id",
    "resolve_linked_gates",
]

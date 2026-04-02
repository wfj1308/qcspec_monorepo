"""Execution-domain integration entry points.

Centralizes external service imports so execution modules depend on a stable
local boundary instead of importing root-level services directly.
"""

from __future__ import annotations

from services.api.boq_utxo_service import resolve_linked_gates
from services.api.did_gate_service import (
    resolve_required_credential,
    verify_credential,
)
from services.api.did_reputation_service import (
    build_did_reputation_summary,
    compute_did_reputation,
)
from services.api.docpeg_proof_chain_service import (
    build_dsp_zip_package,
    build_rebar_report_context,
    get_proof_chain,
    render_rebar_inspection_docx,
    render_rebar_inspection_pdf,
)
from services.api.evidence_center_service import get_all_evidence_for_item
from services.api.labpeg_frequency_remediation_service import (
    calc_inspection_frequency,
    close_remediation_trip,
    get_frequency_dashboard,
    open_remediation_trip,
    record_lab_test,
    remediation_reinspect,
    resolve_dual_pass_gate,
)
from services.api.normpeg_engine import resolve_normpeg_eval
from services.api.phygital_sealing_service import build_sealing_trip
from services.api.proof_utxo_engine import ProofUTXOEngine
from services.api.shadow_ledger_service import sync_to_mirrors
from services.api.sovereign_credit_service import calculate_sovereign_credit
from services.api.specdict_gate_service import (
    evaluate_with_threshold_pack,
    resolve_dynamic_threshold,
)
from services.api.verify_service import get_project_name_by_id

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

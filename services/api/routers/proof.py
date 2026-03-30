"""QCSpec proof routes.
services/api/routers/proof.py
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from supabase import Client

from services.api.dependencies import get_supabase
from services.api.proof_flow_service import (
    aggregate_provenance_chain_flow,
    apply_variation_flow,
    audit_trace_flow,
    bind_utxo_to_spatial_flow,
    auto_settle_from_inspection_flow,
    convert_to_finance_asset_flow,
    consume_utxo_flow,
    boq_item_sovereign_history_flow,
    boq_reconciliation_flow,
    export_doc_final_flow,
    export_finance_proof_flow,
    export_sovereign_om_bundle_flow,
    finalize_docfinal_delivery_flow,
    ingest_sensor_data_flow,
    create_utxo_flow,
    download_docfinal_zip_flow,
    execute_triprole_action_flow,
    get_frequency_dashboard_flow,
    generate_payment_certificate_flow,
    generate_railpact_instruction_flow,
    get_full_lineage_flow,
    get_boq_realtime_status_flow,
    project_readiness_check_flow,
    get_node_tree_flow,
    get_spatial_dashboard_flow,
    get_unit_merkle_root_flow,
    get_docfinal_context_flow,
    get_utxo_chain_flow,
    get_utxo_flow,
    list_proofs_flow,
    list_unspent_utxo_flow,
    list_utxo_transactions_flow,
    predictive_quality_analysis_flow,
    record_lab_test_flow,
    replay_offline_packets_flow,
    calc_inspection_frequency_flow,
    close_remediation_trip_flow,
    open_remediation_trip_flow,
    remediation_reinspect_flow,
    register_om_event_flow,
    rollback_gate_rule_version_flow,
    scan_confirm_signature_flow,
    save_gate_rule_version_flow,
    generate_gate_rules_via_ai_flow,
    get_gate_editor_payload_flow,
    get_spec_dict_flow,
    import_gate_rules_from_norm_flow,
    resolve_dynamic_threshold_flow,
    doc_auto_classify_flow,
    doc_auto_generate_nodes_flow,
    doc_create_node_flow,
    doc_register_upload_flow,
    doc_search_flow,
    doc_tree_flow,
    generate_norm_evolution_report_flow,
    save_spec_dict_flow,
    smu_execute_flow,
    smu_freeze_flow,
    smu_genesis_import_async_flow,
    smu_genesis_import_active_job_flow,
    smu_genesis_import_job_flow,
    smu_genesis_import_flow,
    smu_genesis_preview_flow,
    smu_node_context_flow,
    smu_sign_flow,
    smu_validate_logic_flow,
    proof_stats_flow,
    transfer_asset_flow,
    verify_proof_flow,
)
from services.api.proof_schemas import (
    FrequencyCalcBody,
    DocFinalExportBody,
    DocFinalFinalizeBody,
    DocAutoClassifyBody,
    DocNodeAutoGenerateBody,
    DocNodeCreateBody,
    DocSearchBody,
    FinanceProofExportBody,
    RwaConvertBody,
    SensorIngestBody,
    OfflineReplayBody,
    ScanConfirmBody,
    OMBundleExportBody,
    OMEventBody,
    NormEvolutionBody,
    GateRuleGenerateBody,
    GateRuleNormImportBody,
    GateRuleRollbackBody,
    GateRuleSaveBody,
    LabTestRecordBody,
    SpecDictSaveBody,
    SMUExecuteBody,
    SMUFreezeBody,
    SMUSignBody,
    SMUValidateBody,
    PaymentCertificateBody,
    PredictiveQualityBody,
    RailPactInstructionBody,
    RemediationCloseBody,
    RemediationOpenBody,
    RemediationReinspectBody,
    SpatialBindBody,
    TransferAssetBody,
    TripRoleExecuteBody,
    VariationApplyBody,
    UTXOAutoSettleBody,
    UTXOConsumeBody,
    UTXOCreateBody,
)

router = APIRouter()
public_router = APIRouter()


@router.get("/")
async def list_proofs(
    project_id: str,
    v_uri: Optional[str] = None,
    limit: int = 50,
    sb: Client = Depends(get_supabase),
):
    return await list_proofs_flow(project_id=project_id, v_uri=v_uri, limit=limit, sb=sb)


@router.get("/verify/{proof_id}")
async def verify_proof(
    proof_id: str,
    sb: Client = Depends(get_supabase),
):
    return await verify_proof_flow(proof_id=proof_id, sb=sb)


@router.get("/node-tree")
async def get_node_tree(
    root_uri: str,
    sb: Client = Depends(get_supabase),
):
    return await get_node_tree_flow(root_uri=root_uri, sb=sb)


@router.post("/docs/auto-classify")
async def auto_classify_doc(body: DocAutoClassifyBody, sb: Client = Depends(get_supabase)):
    return await doc_auto_classify_flow(body=body)


@router.get("/docs/tree")
async def get_doc_tree(
    project_uri: str,
    root_uri: str = "",
    sb: Client = Depends(get_supabase),
):
    return doc_tree_flow(project_uri=project_uri, root_uri=root_uri, sb=sb)


@router.post("/docs/node/create")
async def create_doc_node(body: DocNodeCreateBody, sb: Client = Depends(get_supabase)):
    return doc_create_node_flow(body=body, sb=sb)


@router.post("/docs/node/auto-generate")
async def auto_generate_doc_nodes(body: DocNodeAutoGenerateBody, sb: Client = Depends(get_supabase)):
    return doc_auto_generate_nodes_flow(body=body, sb=sb)


@router.post("/docs/search")
async def search_docs(body: DocSearchBody, sb: Client = Depends(get_supabase)):
    return doc_search_flow(body=body, sb=sb)


@router.post("/docs/register")
async def register_doc_upload(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    node_uri: str = Form(""),
    source_utxo_id: str = Form(...),
    executor_uri: str = Form("v://executor/system/"),
    text_excerpt: str = Form(""),
    tags: str = Form(""),
    custom_metadata: str = Form(""),
    ai_metadata: str = Form(""),
    auto_classify: bool = Form(True),
    sb: Client = Depends(get_supabase),
):
    return await doc_register_upload_flow(
        file=file,
        project_uri=project_uri,
        node_uri=node_uri,
        source_utxo_id=source_utxo_id,
        executor_uri=executor_uri,
        text_excerpt=text_excerpt,
        tags=tags,
        custom_metadata=custom_metadata,
        ai_metadata=ai_metadata,
        auto_classify=auto_classify,
        sb=sb,
    )


@router.post("/smu/genesis/import")
async def import_smu_genesis(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    project_id: str = Form(""),
    boq_root_uri: str = Form(""),
    norm_context_root_uri: str = Form(""),
    owner_uri: str = Form(""),
    commit: bool = Form(True),
    sb: Client = Depends(get_supabase),
):
    # Run heavy file parsing / BOQ initialization off the event loop,
    # so one long import won't block unrelated APIs (e.g. auth/login).
    return await run_in_threadpool(
        smu_genesis_import_flow,
        file=file,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        commit=commit,
        sb=sb,
    )


@router.post("/smu/genesis/preview")
async def preview_smu_genesis(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    project_id: str = Form(""),
    boq_root_uri: str = Form(""),
    norm_context_root_uri: str = Form(""),
    owner_uri: str = Form(""),
    sb: Client = Depends(get_supabase),
):
    return await run_in_threadpool(
        smu_genesis_preview_flow,
        file=file,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        sb=sb,
    )


@router.post("/smu/genesis/import-async")
async def import_smu_genesis_async(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    project_id: str = Form(""),
    boq_root_uri: str = Form(""),
    norm_context_root_uri: str = Form(""),
    owner_uri: str = Form(""),
    commit: bool = Form(True),
):
    return smu_genesis_import_async_flow(
        file=file,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        commit=commit,
    )


@router.get("/smu/genesis/import-job/{job_id}")
async def get_smu_genesis_import_job(job_id: str):
    return smu_genesis_import_job_flow(job_id=job_id)


@public_router.get("/smu/genesis/import-job-public/{job_id}")
async def get_smu_genesis_import_job_public(job_id: str):
    return smu_genesis_import_job_flow(job_id=job_id)


@router.get("/smu/genesis/import-job-active")
async def get_smu_genesis_import_job_active(project_uri: str):
    return smu_genesis_import_active_job_flow(project_uri=project_uri)


@public_router.get("/smu/genesis/import-job-active-public")
async def get_smu_genesis_import_job_active_public(project_uri: str):
    return smu_genesis_import_active_job_flow(project_uri=project_uri)


@router.get("/smu/node/context")
async def get_smu_node_context(
    project_uri: str,
    boq_item_uri: str,
    component_type: str = "generic",
    measured_value: Optional[float] = None,
    sb: Client = Depends(get_supabase),
):
    return smu_node_context_flow(
        project_uri=project_uri,
        boq_item_uri=boq_item_uri,
        component_type=component_type,
        measured_value=measured_value,
        sb=sb,
    )


@router.post("/smu/execute")
async def execute_smu_trip(body: SMUExecuteBody, sb: Client = Depends(get_supabase)):
    return smu_execute_flow(body=body, sb=sb)


@router.post("/smu/sign")
async def sign_smu_trip(body: SMUSignBody, sb: Client = Depends(get_supabase)):
    return smu_sign_flow(body=body, sb=sb)


@router.post("/smu/validate-logic")
async def validate_smu_logic(body: SMUValidateBody, sb: Client = Depends(get_supabase)):
    return smu_validate_logic_flow(body=body, sb=sb)


@router.post("/smu/freeze")
async def freeze_smu_asset(body: SMUFreezeBody, sb: Client = Depends(get_supabase)):
    return smu_freeze_flow(body=body, sb=sb)


@router.get("/boq/item-sovereign-history")
async def get_boq_item_sovereign_history(
    project_uri: str,
    subitem_code: str,
    max_rows: int = 50000,
    sb: Client = Depends(get_supabase),
):
    return boq_item_sovereign_history_flow(
        project_uri=project_uri,
        subitem_code=subitem_code,
        max_rows=max_rows,
        sb=sb,
    )


@router.get("/boq/reconciliation")
async def get_boq_reconciliation(
    project_uri: str,
    subitem_code: str = "",
    max_rows: int = 50000,
    limit_items: int = 2000,
    sb: Client = Depends(get_supabase),
):
    return boq_reconciliation_flow(
        project_uri=project_uri,
        subitem_code=subitem_code,
        max_rows=max_rows,
        limit_items=limit_items,
        sb=sb,
    )


@router.get("/stats/{project_id}")
async def proof_stats(
    project_id: str,
    sb: Client = Depends(get_supabase),
):
    return await proof_stats_flow(project_id=project_id, sb=sb)


@router.get("/utxo/unspent")
async def list_unspent_utxo(
    project_uri: str,
    proof_type: Optional[str] = None,
    result: Optional[str] = None,
    segment_uri: Optional[str] = None,
    limit: int = 200,
    sb: Client = Depends(get_supabase),
):
    return list_unspent_utxo_flow(
        project_uri=project_uri,
        proof_type=proof_type,
        result=result,
        segment_uri=segment_uri,
        limit=limit,
        sb=sb,
    )


@router.post("/utxo/create")
async def create_utxo(body: UTXOCreateBody, sb: Client = Depends(get_supabase)):
    return create_utxo_flow(body=body, sb=sb)


@router.post("/utxo/consume")
async def consume_utxo(body: UTXOConsumeBody, sb: Client = Depends(get_supabase)):
    return consume_utxo_flow(body=body, sb=sb)


@router.post("/utxo/auto/inspection-settle")
async def auto_settle_from_inspection(body: UTXOAutoSettleBody, sb: Client = Depends(get_supabase)):
    return auto_settle_from_inspection_flow(body=body, sb=sb)


@router.get("/utxo/{proof_id}")
async def get_utxo(proof_id: str, sb: Client = Depends(get_supabase)):
    return get_utxo_flow(proof_id=proof_id, sb=sb)


@router.get("/utxo/{proof_id}/chain")
async def get_utxo_chain(proof_id: str, sb: Client = Depends(get_supabase)):
    return get_utxo_chain_flow(proof_id=proof_id, sb=sb)


@router.get("/utxo/transactions/list")
async def list_utxo_transactions(
    project_uri: Optional[str] = None,
    limit: int = 100,
    sb: Client = Depends(get_supabase),
):
    return list_utxo_transactions_flow(project_uri=project_uri, limit=limit, sb=sb)


@router.post("/triprole/execute")
async def execute_triprole(body: TripRoleExecuteBody, sb: Client = Depends(get_supabase)):
    return execute_triprole_action_flow(body=body, sb=sb)


@router.post("/triprole/hardware/ingest")
async def ingest_triprole_sensor_data(body: SensorIngestBody, sb: Client = Depends(get_supabase)):
    return ingest_sensor_data_flow(body=body, sb=sb)


@router.post("/lab/record")
async def record_lab_test(body: LabTestRecordBody, sb: Client = Depends(get_supabase)):
    return record_lab_test_flow(body=body, sb=sb)


@router.post("/frequency/calc")
async def calc_frequency(body: FrequencyCalcBody, sb: Client = Depends(get_supabase)):
    return calc_inspection_frequency_flow(body=body, sb=sb)


@router.get("/frequency/dashboard")
async def frequency_dashboard(
    project_uri: str,
    limit_items: int = 200,
    sb: Client = Depends(get_supabase),
):
    return get_frequency_dashboard_flow(
        project_uri=project_uri,
        limit_items=limit_items,
        sb=sb,
    )


@router.get("/triprole/provenance/{utxo_id}")
async def get_triprole_provenance(utxo_id: str, sb: Client = Depends(get_supabase)):
    return aggregate_provenance_chain_flow(utxo_id=utxo_id, sb=sb)


@router.get("/triprole/aggregate-chain/{utxo_id}")
async def get_triprole_aggregate_chain(utxo_id: str, sb: Client = Depends(get_supabase)):
    return aggregate_provenance_chain_flow(utxo_id=utxo_id, sb=sb)


@router.get("/triprole/full-lineage/{utxo_id}")
async def get_triprole_full_lineage(utxo_id: str, sb: Client = Depends(get_supabase)):
    return get_full_lineage_flow(utxo_id=utxo_id, sb=sb)


@router.post("/triprole/transfer-asset")
async def transfer_triprole_asset(body: TransferAssetBody, sb: Client = Depends(get_supabase)):
    return transfer_asset_flow(body=body, sb=sb)


@router.post("/triprole/apply-variation")
async def apply_triprole_variation(body: VariationApplyBody, sb: Client = Depends(get_supabase)):
    return apply_variation_flow(body=body, sb=sb)


@router.post("/triprole/offline/replay")
async def replay_triprole_offline_packets(body: OfflineReplayBody, sb: Client = Depends(get_supabase)):
    return replay_offline_packets_flow(body=body, sb=sb)


@router.post("/triprole/scan-confirm")
async def scan_confirm_triprole_signature(body: ScanConfirmBody, sb: Client = Depends(get_supabase)):
    return scan_confirm_signature_flow(body=body, sb=sb)


@router.post("/remediation/open")
async def open_remediation(body: RemediationOpenBody, sb: Client = Depends(get_supabase)):
    return open_remediation_trip_flow(body=body, sb=sb)


@router.post("/remediation/reinspect")
async def remediation_reinspect(body: RemediationReinspectBody, sb: Client = Depends(get_supabase)):
    return remediation_reinspect_flow(body=body, sb=sb)


@router.post("/remediation/close")
async def close_remediation(body: RemediationCloseBody, sb: Client = Depends(get_supabase)):
    return close_remediation_trip_flow(body=body, sb=sb)


@router.get("/gate-editor/{subitem_code}")
async def get_gate_editor_payload(
    subitem_code: str,
    project_uri: str,
    sb: Client = Depends(get_supabase),
):
    return get_gate_editor_payload_flow(
        project_uri=project_uri,
        subitem_code=subitem_code,
        sb=sb,
    )


@router.post("/gate-editor/import-norm")
async def import_gate_rules_from_norm(body: GateRuleNormImportBody, sb: Client = Depends(get_supabase)):
    return import_gate_rules_from_norm_flow(body=body, sb=sb)


@router.post("/gate-editor/generate-via-ai")
async def generate_gate_rules_via_ai(body: GateRuleGenerateBody, sb: Client = Depends(get_supabase)):
    return generate_gate_rules_via_ai_flow(body=body, sb=sb)


@router.post("/gate-editor/save")
async def save_gate_rule_version(body: GateRuleSaveBody, sb: Client = Depends(get_supabase)):
    return save_gate_rule_version_flow(body=body, sb=sb)


@router.post("/gate-editor/rollback")
async def rollback_gate_rule_version(body: GateRuleRollbackBody, sb: Client = Depends(get_supabase)):
    return rollback_gate_rule_version_flow(body=body, sb=sb)


@router.get("/spec-dict/{spec_dict_key}")
async def get_spec_dict(
    spec_dict_key: str,
    sb: Client = Depends(get_supabase),
):
    return get_spec_dict_flow(spec_dict_key=spec_dict_key, sb=sb)


@router.post("/spec-dict/save")
async def save_spec_dict(body: SpecDictSaveBody, sb: Client = Depends(get_supabase)):
    return save_spec_dict_flow(body=body, sb=sb)


@router.get("/spec-dict-resolve-threshold")
async def resolve_spec_dict_threshold(
    gate_id: str,
    context: str = "",
    sb: Client = Depends(get_supabase),
):
    return resolve_dynamic_threshold_flow(gate_id=gate_id, context=context, sb=sb)


@router.get("/docfinal/context")
async def get_docfinal_context(
    boq_item_uri: str,
    project_name: Optional[str] = None,
    verify_base_url: str = "https://verify.qcspec.com",
    template_path: Optional[str] = None,
    aggregate_anchor_code: str = "",
    aggregate_direction: str = "all",
    aggregate_level: str = "all",
    sb: Client = Depends(get_supabase),
):
    return get_docfinal_context_flow(
        boq_item_uri=boq_item_uri,
        project_name=project_name,
        verify_base_url=verify_base_url,
        template_path=template_path,
        aggregate_anchor_code=aggregate_anchor_code,
        aggregate_direction=aggregate_direction,
        aggregate_level=aggregate_level,
        sb=sb,
    )


@router.get("/docfinal/download")
async def download_docfinal(
    boq_item_uri: str,
    project_name: Optional[str] = None,
    verify_base_url: str = "https://verify.qcspec.com",
    template_path: Optional[str] = None,
    aggregate_anchor_code: str = "",
    aggregate_direction: str = "all",
    aggregate_level: str = "all",
    sb: Client = Depends(get_supabase),
):
    return await download_docfinal_zip_flow(
        boq_item_uri=boq_item_uri,
        project_name=project_name,
        verify_base_url=verify_base_url,
        template_path=template_path,
        aggregate_anchor_code=aggregate_anchor_code,
        aggregate_direction=aggregate_direction,
        aggregate_level=aggregate_level,
        sb=sb,
    )


@router.get("/boq/realtime-status")
async def get_boq_realtime_status(
    project_uri: str,
    sb: Client = Depends(get_supabase),
):
    return get_boq_realtime_status_flow(project_uri=project_uri, sb=sb)


@router.get("/project-readiness-check")
async def get_project_readiness_check(
    project_uri: str,
    sb: Client = Depends(get_supabase),
):
    return project_readiness_check_flow(project_uri=project_uri, sb=sb)


@router.post("/docfinal/export")
async def export_doc_final(body: DocFinalExportBody, sb: Client = Depends(get_supabase)):
    return await export_doc_final_flow(body=body, sb=sb)


@router.post("/payment/certificate/generate")
async def generate_payment_certificate(body: PaymentCertificateBody, sb: Client = Depends(get_supabase)):
    return generate_payment_certificate_flow(body=body, sb=sb)


@router.get("/payment/audit-trace/{payment_id}")
async def payment_audit_trace(
    payment_id: str,
    verify_base_url: str = "https://verify.qcspec.com",
    sb: Client = Depends(get_supabase),
):
    return audit_trace_flow(payment_id=payment_id, verify_base_url=verify_base_url, sb=sb)


@router.post("/payment/railpact/instruction")
async def generate_railpact_instruction(body: RailPactInstructionBody, sb: Client = Depends(get_supabase)):
    return generate_railpact_instruction_flow(body=body, sb=sb)


@router.post("/docfinal/finalize")
async def finalize_docfinal_delivery(body: DocFinalFinalizeBody, sb: Client = Depends(get_supabase)):
    return await finalize_docfinal_delivery_flow(body=body, sb=sb)


@router.post("/spatial/bind")
async def bind_utxo_to_spatial(body: SpatialBindBody, sb: Client = Depends(get_supabase)):
    return bind_utxo_to_spatial_flow(body=body, sb=sb)


@router.get("/spatial/dashboard")
async def get_spatial_dashboard(
    project_uri: str,
    limit: int = 5000,
    sb: Client = Depends(get_supabase),
):
    return get_spatial_dashboard_flow(project_uri=project_uri, limit=limit, sb=sb)


@router.get("/unit/merkle-root")
async def get_unit_merkle_root(
    project_uri: str,
    unit_code: str = "",
    proof_id: str = "",
    max_rows: int = 20000,
    sb: Client = Depends(get_supabase),
):
    return get_unit_merkle_root_flow(
        project_uri=project_uri,
        unit_code=unit_code,
        proof_id=proof_id,
        max_rows=max_rows,
        sb=sb,
    )


@router.post("/ai/predictive-quality")
async def run_predictive_quality_analysis(body: PredictiveQualityBody, sb: Client = Depends(get_supabase)):
    return predictive_quality_analysis_flow(body=body, sb=sb)


@router.post("/finance/proof/export")
async def export_finance_proof(body: FinanceProofExportBody, sb: Client = Depends(get_supabase)):
    return await export_finance_proof_flow(body=body, sb=sb)


@router.post("/rwa/convert")
async def convert_rwa_asset(body: RwaConvertBody, sb: Client = Depends(get_supabase)):
    return await convert_to_finance_asset_flow(body=body, sb=sb)


@router.post("/om/handover/export")
async def export_om_handover_bundle(body: OMBundleExportBody, sb: Client = Depends(get_supabase)):
    return await export_sovereign_om_bundle_flow(body=body, sb=sb)


@router.post("/om/event/register")
async def register_om_event(body: OMEventBody, sb: Client = Depends(get_supabase)):
    return register_om_event_flow(body=body, sb=sb)


@router.post("/norm/evolution/report")
async def generate_norm_evolution_report(body: NormEvolutionBody, sb: Client = Depends(get_supabase)):
    return generate_norm_evolution_report_flow(body=body, sb=sb)

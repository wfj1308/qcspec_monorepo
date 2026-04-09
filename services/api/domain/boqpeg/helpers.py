"""BOQPeg flow helpers used by router/service layers."""

from __future__ import annotations

from typing import Any

from fastapi import UploadFile
from supabase import Client

from services.api.core.http import read_upload_content_sync
from services.api.domain.boqpeg.models import (
    EquipmentTripRequest,
    FormworkUseTripRequest,
    PrestressingTripRequest,
    ToolAssetRegisterRequest,
    WeldingTripRequest,
)
from services.api.domain.boqpeg.integrations import (
    bind_bridge_sub_items,
    bootstrap_normref_logic_scaffold,
    boqpeg_phase1_bridge_pile_report,
    boqpeg_product_manifest,
    create_inspection_batch,
    create_bridge_entity,
    create_process_chain,
    create_pile_entity,
    create_bridge_schedule,
    forward_expand_bom,
    get_active_boqpeg_import_job,
    get_bridge_pile_detail,
    get_pile_entity_detail,
    get_bridge_schedule,
    get_boqpeg_import_job,
    get_full_line_pile_summary,
    get_material_utxo_by_component,
    get_material_utxo_by_iqc,
    get_project_full_line_schedule_summary,
    get_process_materials,
    get_process_chain,
    import_boq_upload_chain,
    match_boq_with_design_manifest,
    parse_design_manifest_from_upload,
    parse_contract_rows_from_upload,
    progress_payment_check,
    preview_boq_upload_chain,
    reverse_conservation_check,
    run_bidirectional_closure,
    start_boqpeg_import_job,
    submit_process_table,
    submit_iqc,
    submit_welding_trip,
    submit_formwork_use_trip,
    submit_prestressing_trip,
    register_tool_asset,
    submit_equipment_trip,
    get_equipment_status,
    get_equipment_history,
    calculate_component_cost,
    sync_bridge_schedule_progress,
    table_to_protocol_block,
    unified_alignment_check,
    update_pile_state_matrix,
    pile_component_uri,
)

_BOQPEG_UPLOAD_MAX_BYTES = 60 * 1024 * 1024


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _read_upload(*, file: UploadFile) -> bytes:
    return read_upload_content_sync(
        file=file,
        max_bytes=_BOQPEG_UPLOAD_MAX_BYTES,
        too_large_error="upload file too large, max 60MB",
    )


def boqpeg_import_flow(
    *,
    file: UploadFile,
    project_uri: str,
    project_id: str,
    boq_root_uri: str,
    norm_context_root_uri: str,
    owner_uri: str,
    bridge_mappings: dict[str, Any] | None = None,
    dto_role: str | None = None,
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    content = _read_upload(file=file)
    return import_boq_upload_chain(
        sb=sb,
        project_uri=project_uri,
        project_id=project_id or None,
        upload_file_name=str(file.filename or "boq.csv"),
        upload_content=content,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        bridge_mappings=bridge_mappings,
        dto_role=dto_role,
        commit=bool(commit),
    )


def boqpeg_preview_flow(
    *,
    file: UploadFile,
    project_uri: str,
    project_id: str,
    boq_root_uri: str,
    norm_context_root_uri: str,
    owner_uri: str,
    bridge_mappings: dict[str, Any] | None = None,
    dto_role: str | None = None,
    sb: Client,
) -> dict[str, Any]:
    content = _read_upload(file=file)
    return preview_boq_upload_chain(
        sb=sb,
        project_uri=project_uri,
        project_id=project_id or None,
        upload_file_name=str(file.filename or "boq.csv"),
        upload_content=content,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        bridge_mappings=bridge_mappings,
        dto_role=dto_role,
    )


def boqpeg_import_async_flow(
    *,
    file: UploadFile,
    project_uri: str,
    project_id: str,
    boq_root_uri: str,
    norm_context_root_uri: str,
    owner_uri: str,
    bridge_mappings: dict[str, Any] | None = None,
    commit: bool,
) -> dict[str, Any]:
    content = _read_upload(file=file)
    return start_boqpeg_import_job(
        upload_file_name=str(file.filename or "boq.csv"),
        upload_content=content,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        bridge_mappings=bridge_mappings,
        commit=bool(commit),
    )


def boqpeg_import_job_flow(*, job_id: str) -> dict[str, Any]:
    return get_boqpeg_import_job(job_id)


def boqpeg_import_active_job_flow(*, project_uri: str) -> dict[str, Any]:
    return get_active_boqpeg_import_job(project_uri=project_uri)


def boqpeg_engine_parse_flow(*, file: UploadFile) -> dict[str, Any]:
    content = _read_upload(file=file)
    return parse_contract_rows_from_upload(
        upload_file_name=str(file.filename or "boq.csv"),
        upload_content=content,
    )


def boqpeg_forward_bom_flow(*, body: dict[str, Any]) -> dict[str, Any]:
    return forward_expand_bom(body=body)


def boqpeg_reverse_conservation_flow(*, body: dict[str, Any]) -> dict[str, Any]:
    return reverse_conservation_check(body=body)


def boqpeg_progress_payment_flow(*, body: dict[str, Any]) -> dict[str, Any]:
    return progress_payment_check(body=body)


def boqpeg_unified_alignment_flow(*, body: dict[str, Any]) -> dict[str, Any]:
    return unified_alignment_check(body=body)


def boqpeg_parse_design_manifest_flow(
    *,
    file: UploadFile,
    project_uri: str,
    design_root_uri: str,
) -> dict[str, Any]:
    content = _read_upload(file=file)
    return parse_design_manifest_from_upload(
        upload_file_name=str(file.filename or "design.ifc"),
        upload_content=content,
        project_uri=project_uri,
        design_root_uri=design_root_uri,
    )


def boqpeg_match_design_boq_flow(
    *,
    file: UploadFile,
    project_uri: str,
    owner_uri: str,
    design_manifest: dict[str, Any],
    deviation_warning_ratio: float,
    deviation_review_ratio: float,
    threshold_spec_uri: str,
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    content = _read_upload(file=file)
    return match_boq_with_design_manifest(
        sb=sb,
        upload_file_name=str(file.filename or "boq.xlsx"),
        upload_content=content,
        project_uri=project_uri,
        owner_uri=owner_uri,
        design_manifest=design_manifest,
        deviation_warning_ratio=deviation_warning_ratio,
        deviation_review_ratio=deviation_review_ratio,
        threshold_spec_uri=threshold_spec_uri,
        commit=bool(commit),
    )


def boqpeg_bidirectional_closure_flow(*, body: dict[str, Any], commit: bool, sb: Client) -> dict[str, Any]:
    return run_bidirectional_closure(sb=sb, body=body, commit=bool(commit))


def boqpeg_create_bridge_entity_flow(
    *,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    return create_bridge_entity(
        sb=sb,
        project_uri=_to_text(body.get("project_uri")).strip(),
        bridge_name=_to_text(body.get("bridge_name")).strip(),
        parent_section=_to_text(body.get("parent_section")).strip(),
        boq_chapter=_to_text(body.get("boq_chapter")).strip() or "400",
        owner_uri=_to_text(body.get("owner_uri")).strip(),
        commit=bool(commit),
    )


def boqpeg_bind_bridge_items_flow(
    *,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    sub_items = body.get("sub_items")
    if not isinstance(sub_items, list):
        sub_items = []
    return bind_bridge_sub_items(
        sb=sb,
        project_uri=_to_text(body.get("project_uri")).strip(),
        bridge_name=_to_text(body.get("bridge_name")).strip(),
        parent_section=_to_text(body.get("parent_section")).strip(),
        boq_chapter=_to_text(body.get("boq_chapter")).strip(),
        sub_items=[item for item in sub_items if isinstance(item, dict)],
        owner_uri=_to_text(body.get("owner_uri")).strip(),
        commit=bool(commit),
    )


def boqpeg_create_pile_entity_flow(
    *,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    boq_item_uris = body.get("boq_item_uris")
    if not isinstance(boq_item_uris, list):
        boq_item_uris = []
    materials = body.get("materials")
    if not isinstance(materials, list):
        materials = []
    qc_report_uris = body.get("qc_report_uris")
    if not isinstance(qc_report_uris, list):
        qc_report_uris = []
    return create_pile_entity(
        sb=sb,
        project_uri=_to_text(body.get("project_uri")).strip(),
        bridge_name=_to_text(body.get("bridge_name")).strip(),
        pile_id=_to_text(body.get("pile_id")).strip(),
        pile_type=_to_text(body.get("pile_type")).strip(),
        length_m=float(body.get("length_m") or 0.0),
        boq_item_uris=[_to_text(x).strip() for x in boq_item_uris if _to_text(x).strip()],
        materials=[_to_text(x).strip() for x in materials if _to_text(x).strip()],
        qc_report_uris=[_to_text(x).strip() for x in qc_report_uris if _to_text(x).strip()],
        state_matrix=body.get("state_matrix") if isinstance(body.get("state_matrix"), dict) else {},
        owner_uri=_to_text(body.get("owner_uri")).strip(),
        commit=bool(commit),
    )


def boqpeg_update_pile_state_flow(
    *,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    return update_pile_state_matrix(
        sb=sb,
        project_uri=_to_text(body.get("project_uri")).strip(),
        bridge_name=_to_text(body.get("bridge_name")).strip(),
        pile_id=_to_text(body.get("pile_id")).strip(),
        updates=body.get("updates") if isinstance(body.get("updates"), dict) else {},
        owner_uri=_to_text(body.get("owner_uri")).strip(),
        commit=bool(commit),
    )


def boqpeg_full_line_piles_flow(*, project_uri: str, sb: Client) -> dict[str, Any]:
    return get_full_line_pile_summary(sb=sb, project_uri=project_uri)


def boqpeg_bridge_piles_flow(*, project_uri: str, bridge_name: str, sb: Client) -> dict[str, Any]:
    return get_bridge_pile_detail(sb=sb, project_uri=project_uri, bridge_name=bridge_name)


def boqpeg_get_pile_entity_flow(*, project_uri: str, bridge_name: str, pile_id: str, sb: Client) -> dict[str, Any]:
    return get_pile_entity_detail(
        sb=sb,
        project_uri=project_uri,
        bridge_name=bridge_name,
        pile_id=pile_id,
    )


def boqpeg_create_bridge_schedule_flow(
    *,
    project_uri: str,
    bridge_name: str,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    return create_bridge_schedule(
        sb=sb,
        project_uri=project_uri,
        bridge_name=bridge_name,
        body=body,
        owner_uri=_to_text(body.get("owner_uri")).strip(),
        commit=bool(commit),
    )


def boqpeg_get_bridge_schedule_flow(*, project_uri: str, bridge_name: str, sb: Client) -> dict[str, Any]:
    return get_bridge_schedule(sb=sb, project_uri=project_uri, bridge_name=bridge_name)


def boqpeg_sync_bridge_schedule_flow(
    *,
    project_uri: str,
    bridge_name: str,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    return sync_bridge_schedule_progress(
        sb=sb,
        project_uri=project_uri,
        bridge_name=bridge_name,
        body=body,
        owner_uri=_to_text(body.get("owner_uri")).strip(),
        commit=bool(commit),
    )


def boqpeg_full_line_schedule_flow(*, project_uri: str, sb: Client) -> dict[str, Any]:
    return get_project_full_line_schedule_summary(sb=sb, project_uri=project_uri)


def boqpeg_create_process_chain_flow(
    *,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    component_uri = _to_text(body.get("component_uri")).strip()
    if not component_uri:
        component_uri = pile_component_uri(
            _to_text(body.get("project_uri")).strip(),
            _to_text(body.get("bridge_name")).strip(),
            _to_text(body.get("pile_id")).strip(),
        )
    return create_process_chain(
        sb=sb,
        project_uri=_to_text(body.get("project_uri")).strip(),
        component_uri=component_uri,
        bridge_uri=_to_text(body.get("bridge_uri")).strip(),
        component_type=_to_text(body.get("component_type")).strip() or "drilled_pile",
        chain_kind=_to_text(body.get("chain_kind")).strip() or "drilled_pile",
        boq_item_ref=_to_text(body.get("boq_item_ref")).strip(),
        steps=[item for item in _as_list(body.get("steps")) if isinstance(item, dict)],
        completed_tables=body.get("completed_tables") if isinstance(body.get("completed_tables"), dict) else {},
        material_state=body.get("material_state") if isinstance(body.get("material_state"), dict) else {},
        owner_uri=_to_text(body.get("owner_uri")).strip(),
        commit=bool(commit),
    )


def boqpeg_get_process_chain_flow(
    *,
    project_uri: str,
    component_uri: str,
    sb: Client,
) -> dict[str, Any]:
    return get_process_chain(
        sb=sb,
        project_uri=project_uri,
        component_uri=component_uri,
    )


def boqpeg_get_process_materials_flow(
    *,
    project_uri: str,
    component_uri: str,
    sb: Client,
) -> dict[str, Any]:
    return get_process_materials(
        sb=sb,
        project_uri=project_uri,
        component_uri=component_uri,
    )


def boqpeg_submit_process_table_flow(
    *,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    component_uri = _to_text(body.get("component_uri")).strip()
    if not component_uri:
        component_uri = pile_component_uri(
            _to_text(body.get("project_uri")).strip(),
            _to_text(body.get("bridge_name")).strip(),
            _to_text(body.get("pile_id")).strip(),
        )
    return submit_process_table(
        sb=sb,
        project_uri=_to_text(body.get("project_uri")).strip(),
        component_uri=component_uri,
        table_name=_to_text(body.get("table_name")).strip(),
        proof_hash=_to_text(body.get("proof_hash")).strip(),
        result=_to_text(body.get("result")).strip() or "PASS",
        owner_uri=_to_text(body.get("owner_uri")).strip(),
        commit=bool(commit),
        chain_snapshot=body.get("chain_snapshot") if isinstance(body.get("chain_snapshot"), dict) else None,
    )


def boqpeg_submit_iqc_flow(
    *,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    result = submit_iqc(
        sb=sb,
        project_uri=_to_text(body.get("project_uri")).strip(),
        component_uri=_to_text(body.get("component_uri")).strip(),
        step_id=_to_text(body.get("step_id")).strip(),
        material_code=_to_text(body.get("material_code")).strip(),
        material_name=_to_text(body.get("material_name")).strip(),
        iqc_form_code=_to_text(body.get("iqc_form_code")).strip(),
        batch_no=_to_text(body.get("batch_no")).strip(),
        total_qty=float(body.get("total_qty") or 0.0),
        unit=_to_text(body.get("unit")).strip(),
        unit_price=float(body.get("unit_price") or 0.0),
        supplier=_to_text(body.get("supplier")).strip(),
        test_results=body.get("test_results") if isinstance(body.get("test_results"), dict) else {},
        executor_uri=_to_text(body.get("executor_uri")).strip(),
        owner_uri=_to_text(body.get("owner_uri")).strip(),
        status=_to_text(body.get("status")).strip() or "approved",
        commit=bool(commit),
    )
    return {"ok": True, "iqc": result.model_dump(mode="json")}


def boqpeg_create_inspection_batch_flow(
    *,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    result = create_inspection_batch(
        sb=sb,
        iqc_uri=_to_text(body.get("iqc_uri")).strip(),
        component_uri=_to_text(body.get("component_uri")).strip(),
        process_step=_to_text(body.get("process_step")).strip(),
        quantity=float(body.get("quantity") or 0.0),
        unit=_to_text(body.get("unit")).strip(),
        inspection_form=_to_text(body.get("inspection_form")).strip(),
        inspection_batch_no=_to_text(body.get("inspection_batch_no")).strip(),
        inspection_result=_to_text(body.get("inspection_result")).strip() or "approved",
        test_results=body.get("test_results") if isinstance(body.get("test_results"), dict) else {},
        executor_uri=_to_text(body.get("executor_uri")).strip(),
        owner_uri=_to_text(body.get("owner_uri")).strip(),
        commit=bool(commit),
    )
    return {"ok": True, "inspection_batch": result.model_dump(mode="json")}


def boqpeg_get_material_utxo_by_iqc_flow(
    *,
    iqc_uri: str,
    sb: Client,
) -> dict[str, Any]:
    out = get_material_utxo_by_iqc(sb=sb, iqc_uri=iqc_uri)
    return {"ok": True, **out.model_dump(mode="json")}


def boqpeg_get_material_utxo_by_component_flow(
    *,
    component_uri: str,
    sb: Client,
) -> dict[str, Any]:
    out = get_material_utxo_by_component(sb=sb, component_uri=component_uri)
    return {"ok": True, **out.model_dump(mode="json")}


async def boqpeg_submit_welding_trip_flow(
    *,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    out = await submit_welding_trip(
        sb=sb,
        body=WeldingTripRequest.model_validate({**body, "commit": bool(commit)}),
        commit=bool(commit),
    )
    return {"ok": True, **out.model_dump(mode="json", by_alias=True)}


async def boqpeg_submit_formwork_use_trip_flow(
    *,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    out = await submit_formwork_use_trip(
        sb=sb,
        body=FormworkUseTripRequest.model_validate({**body, "commit": bool(commit)}),
        commit=bool(commit),
    )
    return {"ok": True, **out.model_dump(mode="json", by_alias=True)}


async def boqpeg_submit_prestressing_trip_flow(
    *,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    out = await submit_prestressing_trip(
        sb=sb,
        body=PrestressingTripRequest.model_validate({**body, "commit": bool(commit)}),
        commit=bool(commit),
    )
    return {"ok": True, **out.model_dump(mode="json", by_alias=True)}


def boqpeg_register_tool_asset_flow(
    *,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    out = register_tool_asset(
        sb=sb,
        body=ToolAssetRegisterRequest.model_validate({**body, "commit": bool(commit)}),
        commit=bool(commit),
    )
    return {"ok": True, "asset": out.model_dump(mode="json", by_alias=True)}


async def boqpeg_submit_equipment_trip_flow(
    *,
    body: dict[str, Any],
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    out = await submit_equipment_trip(
        sb=sb,
        body=EquipmentTripRequest.model_validate({**body, "commit": bool(commit)}),
        commit=bool(commit),
    )
    return {"ok": True, **out.model_dump(mode="json", by_alias=True)}


async def boqpeg_get_equipment_status_flow(
    *,
    equipment_uri: str,
    operator_executor_uri: str,
    sb: Client,
) -> dict[str, Any]:
    out = await get_equipment_status(
        sb=sb,
        equipment_uri=equipment_uri,
        operator_executor_uri=operator_executor_uri,
    )
    return {"ok": True, **out.model_dump(mode="json", by_alias=True)}


async def boqpeg_get_equipment_history_flow(
    *,
    equipment_uri: str,
    sb: Client,
) -> dict[str, Any]:
    out = await get_equipment_history(sb=sb, equipment_uri=equipment_uri)
    return {"ok": True, **out.model_dump(mode="json", by_alias=True)}


def boqpeg_calculate_component_cost_flow(
    *,
    component_uri: str,
    overhead_ratio: float,
    sb: Client,
) -> dict[str, Any]:
    out = calculate_component_cost(sb=sb, component_uri=component_uri, overhead_ratio=overhead_ratio)
    return {"ok": True, **out.model_dump(mode="json")}


def boqpeg_product_manifest_flow() -> dict[str, Any]:
    return boqpeg_product_manifest()


def boqpeg_phase1_bridge_report_flow(*, body: dict[str, Any], commit: bool, sb: Client) -> dict[str, Any]:
    return boqpeg_phase1_bridge_pile_report(sb=sb, body=body, commit=bool(commit))


def boqpeg_normref_logic_scaffold_flow(*, body: dict[str, Any], commit: bool, sb: Client) -> dict[str, Any]:
    return bootstrap_normref_logic_scaffold(
        sb=sb,
        commit=bool(commit),
        owner_uri=_to_text(body.get("owner_uri")).strip() or "v://normref.com/executor/system/",
        write_files=bool(body.get("write_files", False)),
    )


def boqpeg_tab_to_peg_flow(
    *,
    file: UploadFile,
    protocol_uri: str,
    norm_code: str,
    boq_item_id: str,
    description: str,
    bridge_uri: str,
    component_type: str,
    topology_component_count: int,
    forms_per_component: int,
    generated_qc_table_count: int,
    signed_pass_table_count: int,
    owner_uri: str,
    commit: bool,
    sb: Client,
) -> dict[str, Any]:
    content = _read_upload(file=file)
    return table_to_protocol_block(
        sb=sb,
        upload_file_name=str(file.filename or "quality-table.csv"),
        upload_content=content,
        protocol_uri=protocol_uri,
        norm_code=norm_code,
        boq_item_id=boq_item_id,
        description=description,
        bridge_uri=bridge_uri,
        component_type=component_type,
        topology_component_count=int(topology_component_count or 0),
        forms_per_component=int(forms_per_component or 2),
        generated_qc_table_count=int(generated_qc_table_count or 0),
        signed_pass_table_count=int(signed_pass_table_count or 0),
        owner_uri=owner_uri,
        commit=bool(commit),
        write_files=bool(commit),
    )


__all__ = [
    "boqpeg_bidirectional_closure_flow",
    "boqpeg_bind_bridge_items_flow",
    "boqpeg_bridge_piles_flow",
    "boqpeg_create_bridge_entity_flow",
    "boqpeg_create_inspection_batch_flow",
    "boqpeg_create_pile_entity_flow",
    "boqpeg_create_bridge_schedule_flow",
    "boqpeg_create_process_chain_flow",
    "boqpeg_phase1_bridge_report_flow",
    "boqpeg_product_manifest_flow",
    "boqpeg_engine_parse_flow",
    "boqpeg_full_line_piles_flow",
    "boqpeg_get_pile_entity_flow",
    "boqpeg_full_line_schedule_flow",
    "boqpeg_forward_bom_flow",
    "boqpeg_get_bridge_schedule_flow",
    "boqpeg_get_material_utxo_by_component_flow",
    "boqpeg_get_material_utxo_by_iqc_flow",
    "boqpeg_submit_welding_trip_flow",
    "boqpeg_submit_formwork_use_trip_flow",
    "boqpeg_submit_prestressing_trip_flow",
    "boqpeg_register_tool_asset_flow",
    "boqpeg_submit_equipment_trip_flow",
    "boqpeg_get_equipment_status_flow",
    "boqpeg_get_equipment_history_flow",
    "boqpeg_calculate_component_cost_flow",
    "boqpeg_get_process_materials_flow",
    "boqpeg_get_process_chain_flow",
    "boqpeg_normref_logic_scaffold_flow",
    "boqpeg_import_active_job_flow",
    "boqpeg_import_async_flow",
    "boqpeg_import_flow",
    "boqpeg_import_job_flow",
    "boqpeg_match_design_boq_flow",
    "boqpeg_parse_design_manifest_flow",
    "boqpeg_progress_payment_flow",
    "boqpeg_preview_flow",
    "boqpeg_reverse_conservation_flow",
    "boqpeg_tab_to_peg_flow",
    "boqpeg_sync_bridge_schedule_flow",
    "boqpeg_submit_process_table_flow",
    "boqpeg_submit_iqc_flow",
    "boqpeg_unified_alignment_flow",
    "boqpeg_update_pile_state_flow",
]

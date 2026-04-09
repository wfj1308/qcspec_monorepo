"""BOQPeg integration entry points."""

from __future__ import annotations

from importlib import import_module
from typing import Any


def _runtime() -> Any:
    return import_module("services.api.domain.boqpeg.runtime")


def parse_boq_upload(*args: Any, **kwargs: Any) -> Any:
    return _runtime().parse_boq_upload(*args, **kwargs)


def initialize_boq_genesis_chain(*args: Any, **kwargs: Any) -> Any:
    return _runtime().initialize_boq_genesis_chain(*args, **kwargs)


def import_boq_upload_chain(*args: Any, **kwargs: Any) -> Any:
    return _runtime().import_boq_upload_chain(*args, **kwargs)

def scan_boq_and_create_utxos(*args: Any, **kwargs: Any) -> Any:
    return _runtime().scan_boq_and_create_utxos(*args, **kwargs)


def preview_boq_upload_chain(*args: Any, **kwargs: Any) -> Any:
    return _runtime().preview_boq_upload_chain(*args, **kwargs)


def start_boqpeg_import_job(*args: Any, **kwargs: Any) -> Any:
    return _runtime().start_boqpeg_import_job(*args, **kwargs)


def get_boqpeg_import_job(*args: Any, **kwargs: Any) -> Any:
    return _runtime().get_boqpeg_import_job(*args, **kwargs)


def get_active_boqpeg_import_job(*args: Any, **kwargs: Any) -> Any:
    return _runtime().get_active_boqpeg_import_job(*args, **kwargs)


def validate_ref_only_rows(*args: Any, **kwargs: Any) -> Any:
    return _runtime().validate_ref_only_rows(*args, **kwargs)

def map_spu_to_boq_preview_rows(*args: Any, **kwargs: Any) -> Any:
    return _runtime().map_spu_to_boq_preview_rows(*args, **kwargs)


def parse_contract_rows_from_upload(*args: Any, **kwargs: Any) -> Any:
    return _runtime().parse_contract_rows_from_upload(*args, **kwargs)


def forward_expand_bom(*args: Any, **kwargs: Any) -> Any:
    return _runtime().forward_expand_bom(*args, **kwargs)


def reverse_conservation_check(*args: Any, **kwargs: Any) -> Any:
    return _runtime().reverse_conservation_check(*args, **kwargs)


def progress_payment_check(*args: Any, **kwargs: Any) -> Any:
    return _runtime().progress_payment_check(*args, **kwargs)


def unified_alignment_check(*args: Any, **kwargs: Any) -> Any:
    return _runtime().unified_alignment_check(*args, **kwargs)


def parse_design_manifest_from_upload(*args: Any, **kwargs: Any) -> Any:
    return _runtime().parse_design_manifest_from_upload(*args, **kwargs)


def match_boq_with_design_manifest(*args: Any, **kwargs: Any) -> Any:
    return _runtime().match_boq_with_design_manifest(*args, **kwargs)


def run_bidirectional_closure(*args: Any, **kwargs: Any) -> Any:
    return _runtime().run_bidirectional_closure(*args, **kwargs)


def create_bridge_entity(*args: Any, **kwargs: Any) -> Any:
    return _runtime().create_bridge_entity(*args, **kwargs)


def create_pile_entity(*args: Any, **kwargs: Any) -> Any:
    return _runtime().create_pile_entity(*args, **kwargs)


def bind_bridge_sub_items(*args: Any, **kwargs: Any) -> Any:
    return _runtime().bind_bridge_sub_items(*args, **kwargs)


def get_full_line_pile_summary(*args: Any, **kwargs: Any) -> Any:
    return _runtime().get_full_line_pile_summary(*args, **kwargs)


def get_bridge_pile_detail(*args: Any, **kwargs: Any) -> Any:
    return _runtime().get_bridge_pile_detail(*args, **kwargs)


def get_pile_entity_detail(*args: Any, **kwargs: Any) -> Any:
    return _runtime().get_pile_entity_detail(*args, **kwargs)


def update_pile_state_matrix(*args: Any, **kwargs: Any) -> Any:
    return _runtime().update_pile_state_matrix(*args, **kwargs)


def create_bridge_schedule(*args: Any, **kwargs: Any) -> Any:
    return _runtime().create_bridge_schedule(*args, **kwargs)


def get_bridge_schedule(*args: Any, **kwargs: Any) -> Any:
    return _runtime().get_bridge_schedule(*args, **kwargs)


def sync_bridge_schedule_progress(*args: Any, **kwargs: Any) -> Any:
    return _runtime().sync_bridge_schedule_progress(*args, **kwargs)


def get_project_full_line_schedule_summary(*args: Any, **kwargs: Any) -> Any:
    return _runtime().get_project_full_line_schedule_summary(*args, **kwargs)


def pile_component_uri(*args: Any, **kwargs: Any) -> Any:
    return _runtime().pile_component_uri(*args, **kwargs)


def create_process_chain(*args: Any, **kwargs: Any) -> Any:
    return _runtime().create_process_chain(*args, **kwargs)


def get_process_chain(*args: Any, **kwargs: Any) -> Any:
    return _runtime().get_process_chain(*args, **kwargs)


def get_process_materials(*args: Any, **kwargs: Any) -> Any:
    return _runtime().get_process_materials(*args, **kwargs)


def submit_process_table(*args: Any, **kwargs: Any) -> Any:
    return _runtime().submit_process_table(*args, **kwargs)


def submit_iqc(*args: Any, **kwargs: Any) -> Any:
    return _runtime().submit_iqc(*args, **kwargs)


def create_inspection_batch(*args: Any, **kwargs: Any) -> Any:
    return _runtime().create_inspection_batch(*args, **kwargs)


def get_material_utxo_by_iqc(*args: Any, **kwargs: Any) -> Any:
    return _runtime().get_material_utxo_by_iqc(*args, **kwargs)


def get_material_utxo_by_component(*args: Any, **kwargs: Any) -> Any:
    return _runtime().get_material_utxo_by_component(*args, **kwargs)


def summarize_component_step_materials(*args: Any, **kwargs: Any) -> Any:
    return _runtime().summarize_component_step_materials(*args, **kwargs)


def summarize_component_material_cost(*args: Any, **kwargs: Any) -> Any:
    return _runtime().summarize_component_material_cost(*args, **kwargs)


def submit_welding_trip(*args: Any, **kwargs: Any) -> Any:
    return _runtime().submit_welding_trip(*args, **kwargs)


def submit_formwork_use_trip(*args: Any, **kwargs: Any) -> Any:
    return _runtime().submit_formwork_use_trip(*args, **kwargs)


def submit_prestressing_trip(*args: Any, **kwargs: Any) -> Any:
    return _runtime().submit_prestressing_trip(*args, **kwargs)


def calculate_component_cost(*args: Any, **kwargs: Any) -> Any:
    return _runtime().calculate_component_cost(*args, **kwargs)


def register_tool_asset(*args: Any, **kwargs: Any) -> Any:
    return _runtime().register_tool_asset(*args, **kwargs)


def submit_equipment_trip(*args: Any, **kwargs: Any) -> Any:
    return _runtime().submit_equipment_trip(*args, **kwargs)


def get_equipment_status(*args: Any, **kwargs: Any) -> Any:
    return _runtime().get_equipment_status(*args, **kwargs)


def get_equipment_history(*args: Any, **kwargs: Any) -> Any:
    return _runtime().get_equipment_history(*args, **kwargs)


def sum_equipment_trip_cost(*args: Any, **kwargs: Any) -> Any:
    return _runtime().sum_equipment_trip_cost(*args, **kwargs)


def boqpeg_product_manifest(*args: Any, **kwargs: Any) -> Any:
    return _runtime().boqpeg_product_manifest(*args, **kwargs)


def boqpeg_phase1_bridge_pile_report(*args: Any, **kwargs: Any) -> Any:
    return _runtime().boqpeg_phase1_bridge_pile_report(*args, **kwargs)


def bootstrap_normref_logic_scaffold(*args: Any, **kwargs: Any) -> Any:
    return _runtime().bootstrap_normref_logic_scaffold(*args, **kwargs)


def table_to_protocol_block(*args: Any, **kwargs: Any) -> Any:
    return _runtime().table_to_protocol_block(*args, **kwargs)


__all__ = [
    "bind_bridge_sub_items",
    "boqpeg_phase1_bridge_pile_report",
    "boqpeg_product_manifest",
    "bootstrap_normref_logic_scaffold",
    "create_bridge_entity",
    "create_process_chain",
    "create_pile_entity",
    "create_bridge_schedule",
    "forward_expand_bom",
    "get_active_boqpeg_import_job",
    "get_bridge_pile_detail",
    "get_pile_entity_detail",
    "get_bridge_schedule",
    "get_boqpeg_import_job",
    "get_full_line_pile_summary",
    "get_project_full_line_schedule_summary",
    "get_process_chain",
    "get_process_materials",
    "import_boq_upload_chain",
    "scan_boq_and_create_utxos",
    "initialize_boq_genesis_chain",
    "match_boq_with_design_manifest",
    "parse_contract_rows_from_upload",
    "parse_design_manifest_from_upload",
    "parse_boq_upload",
    "progress_payment_check",
    "pile_component_uri",
    "preview_boq_upload_chain",
    "reverse_conservation_check",
    "run_bidirectional_closure",
    "start_boqpeg_import_job",
    "submit_process_table",
    "submit_iqc",
    "create_inspection_batch",
    "submit_welding_trip",
    "submit_formwork_use_trip",
    "submit_prestressing_trip",
    "register_tool_asset",
    "submit_equipment_trip",
    "get_equipment_status",
    "get_equipment_history",
    "sum_equipment_trip_cost",
    "calculate_component_cost",
    "get_material_utxo_by_iqc",
    "get_material_utxo_by_component",
    "summarize_component_step_materials",
    "summarize_component_material_cost",
    "sync_bridge_schedule_progress",
    "table_to_protocol_block",
    "unified_alignment_check",
    "update_pile_state_matrix",
    "validate_ref_only_rows",
    "map_spu_to_boq_preview_rows",
]

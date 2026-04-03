"""Master DocFinal export orchestration."""

from __future__ import annotations

from typing import Any, Callable


def export_doc_final(
    *,
    sb: Any,
    project_uri: str,
    project_name: str | None = None,
    passphrase: str = "",
    verify_base_url: str = "https://verify.qcspec.com",
    include_unsettled: bool = False,
    get_boq_realtime_status_fn: Callable[..., dict[str, Any]],
    proof_utxo_engine_cls: Callable[[Any], Any],
    export_doc_final_archive_fn: Callable[..., dict[str, Any]],
    build_docfinal_package_for_boq_fn: Callable[..., dict[str, Any]],
    get_full_lineage_fn: Callable[..., dict[str, Any]],
    item_no_from_boq_uri_fn: Callable[[str], str],
    smu_id_from_item_no_fn: Callable[[str], str],
    utc_iso_fn: Callable[[], str],
    encrypt_aes256_fn: Callable[[bytes, str], bytes],
) -> dict[str, Any]:
    status = get_boq_realtime_status_fn(sb=sb, project_uri=project_uri, limit=10000)
    engine = proof_utxo_engine_cls(sb)
    return export_doc_final_archive_fn(
        status=status,
        sb=sb,
        project_uri=project_uri,
        project_name=project_name,
        passphrase=passphrase,
        verify_base_url=verify_base_url,
        include_unsettled=include_unsettled,
        build_docfinal_package_for_boq_fn=build_docfinal_package_for_boq_fn,
        get_full_lineage_fn=get_full_lineage_fn,
        item_no_from_boq_uri_fn=item_no_from_boq_uri_fn,
        smu_id_from_item_no_fn=smu_id_from_item_no_fn,
        utc_iso_fn=utc_iso_fn,
        encrypt_aes256_fn=encrypt_aes256_fn,
        create_birth_row_fn=lambda proof_id, owner_uri, normalized_project_uri, birth_state, segment_uri: engine.create(
            proof_id=proof_id,
            owner_uri=owner_uri,
            project_uri=normalized_project_uri,
            project_id=None,
            proof_type="archive",
            result="PASS",
            state_data=birth_state,
            conditions=[],
            parent_proof_id=None,
            norm_uri="v://norm/CoordOS/DocFinal/1.0#master_dsp",
            segment_uri=segment_uri,
            signer_uri=owner_uri,
            signer_role="SYSTEM",
        ),
    )

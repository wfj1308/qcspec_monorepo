"""Internal helpers for proof-domain replay and DocFinal delivery flows."""

from __future__ import annotations

import io
from typing import Any

from fastapi.responses import StreamingResponse

from services.api.boq_payment_audit_service import finalize_docfinal_delivery
from services.api.triprole_engine import build_docfinal_package_for_boq, export_doc_final, replay_offline_packets


def replay_offline_packets_payload(*, body: Any, sb: Any) -> dict[str, Any]:
    packets = [
        (x.model_dump() if hasattr(x, "model_dump") else dict(x))
        for x in list(body.packets or [])
    ]
    return replay_offline_packets(
        sb=sb,
        packets=packets,
        stop_on_error=bool(body.stop_on_error),
        default_executor_uri=str(body.default_executor_uri or "v://executor/system/"),
        default_executor_role=str(body.default_executor_role or "TRIPROLE"),
    )


def get_docfinal_context(
    *,
    boq_item_uri: str,
    project_name: str | None,
    verify_base_url: str,
    template_path: str | None,
    aggregate_anchor_code: str,
    aggregate_direction: str,
    aggregate_level: str,
    sb: Any,
) -> dict[str, Any]:
    project_meta = {"project_name": project_name} if project_name else {}
    package = build_docfinal_package_for_boq(
        boq_item_uri=boq_item_uri,
        sb=sb,
        project_meta=project_meta,
        verify_base_url=verify_base_url,
        template_path=template_path,
        aggregate_anchor_code=aggregate_anchor_code,
        aggregate_direction=aggregate_direction,
        aggregate_level=aggregate_level,
        apply_asset_transfer=False,
    )
    return {
        "ok": True,
        "boq_item_uri": boq_item_uri,
        "chain_count": len(package.get("proof_chain") or []),
        "context": package.get("context") or {},
        "full_lineage": package.get("full_lineage") or {},
    }


async def download_docfinal_zip(
    *,
    boq_item_uri: str,
    project_name: str | None,
    verify_base_url: str,
    template_path: str | None,
    aggregate_anchor_code: str,
    aggregate_direction: str,
    aggregate_level: str,
    sb: Any,
) -> StreamingResponse:
    project_meta = {"project_name": project_name} if project_name else {}
    package = build_docfinal_package_for_boq(
        boq_item_uri=boq_item_uri,
        sb=sb,
        project_meta=project_meta,
        verify_base_url=verify_base_url,
        template_path=template_path,
        aggregate_anchor_code=aggregate_anchor_code,
        aggregate_direction=aggregate_direction,
        aggregate_level=aggregate_level,
    )
    filename = f"DOCFINAL-{package.get('filename_base') or 'boq'}.zip"
    return StreamingResponse(
        io.BytesIO(package.get("zip_bytes") or b""),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def export_doc_final_package(*, body: Any, sb: Any) -> StreamingResponse:
    result = export_doc_final(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        project_name=str(body.project_name or ""),
        passphrase=str(body.passphrase or ""),
        verify_base_url=str(body.verify_base_url or "https://verify.qcspec.com"),
        include_unsettled=bool(body.include_unsettled),
    )
    return StreamingResponse(
        io.BytesIO(result.get("encrypted_bytes") or b""),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{result.get("filename") or "MASTER-DSP.qcdsp"}"',
            "X-DocFinal-Root-Hash": str(result.get("root_hash") or ""),
            "X-DocFinal-Proof-Id": str((result.get("birth_certificate") or {}).get("proof_id") or ""),
            "X-DocFinal-GitPeg-Anchor": str((result.get("birth_certificate") or {}).get("gitpeg_anchor") or ""),
        },
    )


async def finalize_docfinal_delivery_package(*, body: Any, sb: Any) -> StreamingResponse:
    result = finalize_docfinal_delivery(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        project_name=str(body.project_name or ""),
        passphrase=str(body.passphrase or ""),
        verify_base_url=str(body.verify_base_url or "https://verify.qcspec.com"),
        include_unsettled=bool(body.include_unsettled),
        run_anchor_rounds=int(body.run_anchor_rounds or 0),
    )
    return StreamingResponse(
        io.BytesIO(result.get("encrypted_bytes") or b""),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{result.get("filename") or "MASTER-DSP.qcdsp"}"',
            "X-DocFinal-Root-Hash": str(result.get("root_hash") or ""),
            "X-DocFinal-Proof-Id": str((result.get("birth_certificate") or {}).get("proof_id") or ""),
            "X-DocFinal-GitPeg-Anchor": str((result.get("birth_certificate") or {}).get("gitpeg_anchor") or ""),
            "X-DocFinal-Final-GitPeg-Anchor": str(result.get("final_gitpeg_anchor") or ""),
            "X-DocFinal-Anchor-Runs": str(len(result.get("anchor_runs") or [])),
        },
    )

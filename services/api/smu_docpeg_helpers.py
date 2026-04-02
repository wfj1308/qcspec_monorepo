"""Shared DocPeg helpers used by SMU signing flows."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import re
from typing import Any, Callable

from services.api.domain.documents.integrations import register_document
from services.api.domain.execution.flows import build_docfinal_package_for_boq
from services.api.reports_generation_service import REPORTS_BUCKET
from services.api.smu_primitives import (
    as_dict as _as_dict,
    to_text as _to_text,
)


def _safe_name(value: str, fallback: str = "doc") -> str:
    text = _to_text(value).strip()
    text = re.sub(r"[^\w.\-]+", "_", text, flags=re.ASCII).strip("_")
    return text or fallback


def _docpeg_report_no(item_no: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe_item = _safe_name(item_no or "", "ITEM")
    return f"DOCPEG-{safe_item}-{now}"


def _upload_docpeg_pdf(
    *,
    sb: Any,
    project_uri: str,
    report_no: str,
    pdf_bytes: bytes,
) -> tuple[str, str]:
    project_key = _safe_name(project_uri.replace("v://", "v_"), "project")
    file_name = f"{_safe_name(report_no, 'DOCPEG')}.pdf"
    storage_path = f"{project_key}/docpeg/{file_name}"
    sb.storage.from_(REPORTS_BUCKET).upload(
        storage_path,
        pdf_bytes,
        file_options={"content-type": "application/pdf"},
    )
    public_url = sb.storage.from_(REPORTS_BUCKET).get_public_url(storage_path)
    storage_url = public_url if isinstance(public_url, str) else ""
    return storage_path, storage_url


def resolve_docpeg_package(
    *,
    sb: Any,
    item_uri: str,
    input_smu_id: str,
    verify_base_url: str,
    selected_template_path: str,
) -> dict[str, Any]:
    package = build_docfinal_package_for_boq(
        boq_item_uri=item_uri,
        sb=sb,
        project_meta={},
        verify_base_url=verify_base_url,
        template_path=selected_template_path or None,
        apply_asset_transfer=False,
    )
    context = _as_dict(package.get("context"))
    context["smu_id"] = input_smu_id
    risk_audit = _as_dict(context.get("risk_audit"))
    pdf_bytes = package.get("pdf_bytes") or b""
    preview_bytes = bytes(pdf_bytes[:1_800_000])
    return {
        "package": package,
        "context": context,
        "risk_audit": risk_audit,
        "pdf_bytes": pdf_bytes,
        "preview_bytes": preview_bytes,
    }


def register_docpeg_pdf_document(
    *,
    sb: Any,
    project_uri: str,
    report_no: str,
    pdf_bytes: bytes,
    item_uri: str,
    out_id: str,
    in_id: str,
    selected_template_path: str,
    supervisor_executor_uri: str,
) -> tuple[dict[str, Any], str]:
    storage_path, storage_url = _upload_docpeg_pdf(
        sb=sb,
        project_uri=project_uri,
        report_no=report_no,
        pdf_bytes=pdf_bytes,
    )
    docpeg_document = register_document(
        sb=sb,
        project_uri=project_uri,
        node_uri=f"{item_uri.rstrip('/')}/reports/{report_no}/",
        source_utxo_id=out_id or in_id,
        file_name=f"{report_no}.pdf",
        file_size=len(pdf_bytes),
        mime_type="application/pdf",
        storage_path=storage_path,
        storage_url=storage_url,
        text_excerpt="DocPeg auto-rendered report",
        ai_metadata={
            "doc_type": "docpeg_report",
            "summary": "DocPeg auto-rendered report",
            "tags": ["docpeg", "docfinal", "report"],
        },
        custom_metadata={
            "report_no": report_no,
            "boq_item_uri": item_uri,
            "template_path": selected_template_path,
        },
        tags=["docpeg", "docfinal", "report"],
        executor_uri=supervisor_executor_uri or "v://executor/docpeg/system/",
        trip_action="document.create_trip",
        lifecycle_stage="DOCUMENT",
        trip_payload={
            "phase": "DocPeg.render",
            "source": "OrdoSign",
            "report_no": report_no,
        },
    )
    docpeg_document["report_no"] = report_no
    return _as_dict(docpeg_document), storage_url


def push_docpeg_erpnext_with_fallback(
    *,
    sb: Any,
    project_id: str,
    project_uri: str,
    boq_item_uri: str,
    item_no: str,
    item_name: str,
    report_no: str,
    report_url: str,
    docpeg_document: dict[str, Any],
    context: dict[str, Any],
    risk_audit: dict[str, Any],
    out_id: str,
    in_id: str,
    push_docpeg_to_erpnext: Callable[..., dict[str, Any]],
    create_erpnext_receipt_proof: Callable[..., dict[str, Any]],
    queue_erpnext_push: Callable[..., None],
) -> tuple[dict[str, Any], dict[str, Any]]:
    erpnext_push = push_docpeg_to_erpnext(
        sb=sb,
        project_id=project_id,
        project_uri=project_uri,
        item_no=item_no,
        item_name=item_name,
        report_no=report_no,
        report_url=report_url,
        docpeg_document=docpeg_document,
        docpeg_context=context,
        risk_audit=risk_audit,
    )
    erpnext_receipt: dict[str, Any] = {}
    if bool(erpnext_push.get("success")):
        erpnext_receipt = _as_dict(
            create_erpnext_receipt_proof(
                sb=sb,
                project_uri=project_uri,
                boq_item_uri=boq_item_uri,
                payload=_as_dict(erpnext_push.get("payload")),
                response=erpnext_push,
                source_utxo_id=out_id or in_id,
            )
        )
    else:
        queue_erpnext_push(
            sb=sb,
            project_uri=project_uri,
            boq_item_uri=boq_item_uri,
            payload=_as_dict(erpnext_push.get("payload")),
            response=erpnext_push,
        )
    return _as_dict(erpnext_push), erpnext_receipt


def persist_docpeg_document_and_erpnext(
    *,
    sb: Any,
    project_uri: str,
    project_id: str,
    report_no: str,
    pdf_bytes: bytes,
    item_uri: str,
    out_id: str,
    in_id: str,
    selected_template_path: str,
    supervisor_executor_uri: str,
    input_item_no: str,
    input_item_name: str,
    context: dict[str, Any],
    risk_audit: dict[str, Any],
    push_docpeg_to_erpnext: Callable[..., dict[str, Any]],
    create_erpnext_receipt_proof: Callable[..., dict[str, Any]],
    queue_erpnext_push: Callable[..., None],
) -> dict[str, Any]:
    docpeg_document: dict[str, Any] = {}
    erpnext_push: dict[str, Any] = {}
    erpnext_receipt: dict[str, Any] = {}
    if not project_uri or not pdf_bytes:
        return {
            "docpeg_document": docpeg_document,
            "erpnext_push": erpnext_push,
            "erpnext_receipt": erpnext_receipt,
        }
    try:
        docpeg_document, storage_url = register_docpeg_pdf_document(
            sb=sb,
            project_uri=project_uri,
            report_no=report_no,
            pdf_bytes=pdf_bytes,
            item_uri=item_uri,
            out_id=out_id,
            in_id=in_id,
            selected_template_path=selected_template_path,
            supervisor_executor_uri=supervisor_executor_uri,
        )
        erpnext_push, erpnext_receipt = push_docpeg_erpnext_with_fallback(
            sb=sb,
            project_id=project_id,
            project_uri=project_uri,
            boq_item_uri=item_uri,
            item_no=input_item_no,
            item_name=input_item_name,
            report_no=report_no,
            report_url=storage_url,
            docpeg_document=docpeg_document,
            context=context,
            risk_audit=risk_audit,
            out_id=out_id,
            in_id=in_id,
            push_docpeg_to_erpnext=push_docpeg_to_erpnext,
            create_erpnext_receipt_proof=create_erpnext_receipt_proof,
            queue_erpnext_push=queue_erpnext_push,
        )
    except Exception as exc:
        docpeg_document = {
            "ok": False,
            "error": f"{exc.__class__.__name__}: {exc}",
            "report_no": report_no,
        }
    return {
        "docpeg_document": docpeg_document,
        "erpnext_push": erpnext_push,
        "erpnext_receipt": erpnext_receipt,
    }


def build_docpeg_bundle(
    *,
    package: dict[str, Any],
    context: dict[str, Any],
    preview_bytes: bytes,
    pdf_bytes: bytes,
    template_binding: dict[str, Any],
    selected_template_path: str,
    docpeg_document: dict[str, Any],
    risk_audit: dict[str, Any],
    erpnext_push: dict[str, Any],
    erpnext_receipt: dict[str, Any],
) -> dict[str, Any]:
    docpeg = {
        "verify_uri": _to_text(context.get("verify_uri") or "").strip(),
        "artifact_uri": _to_text(context.get("artifact_uri") or "").strip(),
        "gitpeg_anchor": _to_text(context.get("gitpeg_anchor") or "").strip(),
        "pdf_preview_b64": base64.b64encode(preview_bytes).decode("ascii") if preview_bytes else "",
        "pdf_preview_truncated": len(preview_bytes) < len(pdf_bytes),
        "template_binding": template_binding,
        "selected_template_path": selected_template_path or _to_text(template_binding.get("fallback_template") or "").strip(),
        "context": package.get("context") or {},
        "document": docpeg_document or {},
        "risk_audit": risk_audit,
        "erpnext_push": erpnext_push,
        "erpnext_receipt": erpnext_receipt,
    }
    return {
        "docpeg": docpeg,
        "docpeg_document": docpeg_document,
        "risk_audit": risk_audit,
        "erpnext_push": erpnext_push,
        "erpnext_receipt": erpnext_receipt,
    }


def run_auto_docpeg_after_sign(
    *,
    sb: Any,
    item_uri: str,
    in_id: str,
    out_id: str,
    input_row: dict[str, Any],
    input_item_no: str,
    input_item_name: str,
    input_smu_id: str,
    template_binding: dict[str, Any],
    selected_template_path: str,
    verify_base_url: str,
    supervisor_executor_uri: str,
    push_docpeg_to_erpnext: Callable[..., dict[str, Any]],
    create_erpnext_receipt_proof: Callable[..., dict[str, Any]],
    queue_erpnext_push: Callable[..., None],
) -> dict[str, Any]:
    package_bundle = resolve_docpeg_package(
        sb=sb,
        item_uri=item_uri,
        input_smu_id=input_smu_id,
        verify_base_url=verify_base_url,
        selected_template_path=selected_template_path,
    )
    package = _as_dict(package_bundle.get("package"))
    context = _as_dict(package_bundle.get("context"))
    risk_audit = _as_dict(package_bundle.get("risk_audit"))
    pdf_bytes = bytes(package_bundle.get("pdf_bytes") or b"")
    preview_bytes = bytes(package_bundle.get("preview_bytes") or b"")
    report_no = _docpeg_report_no(input_item_no)
    project_uri = _to_text(input_row.get("project_uri") or "").strip()

    persisted = persist_docpeg_document_and_erpnext(
        sb=sb,
        project_uri=project_uri,
        project_id=_to_text(input_row.get("project_id") or "").strip(),
        report_no=report_no,
        pdf_bytes=pdf_bytes,
        item_uri=item_uri,
        out_id=out_id,
        in_id=in_id,
        selected_template_path=selected_template_path,
        supervisor_executor_uri=supervisor_executor_uri,
        input_item_no=input_item_no,
        input_item_name=input_item_name,
        context=context,
        risk_audit=risk_audit,
        push_docpeg_to_erpnext=push_docpeg_to_erpnext,
        create_erpnext_receipt_proof=create_erpnext_receipt_proof,
        queue_erpnext_push=queue_erpnext_push,
    )
    docpeg_document = _as_dict(persisted.get("docpeg_document"))
    erpnext_push = _as_dict(persisted.get("erpnext_push"))
    erpnext_receipt = _as_dict(persisted.get("erpnext_receipt"))
    return build_docpeg_bundle(
        package=package,
        context=context,
        preview_bytes=preview_bytes,
        pdf_bytes=pdf_bytes,
        template_binding=template_binding,
        selected_template_path=selected_template_path,
        docpeg_document=docpeg_document,
        risk_audit=risk_audit,
        erpnext_push=erpnext_push,
        erpnext_receipt=erpnext_receipt,
    )


__all__ = [
    "run_auto_docpeg_after_sign",
]

"""DocFinal rendering and DSP packaging helpers."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Callable


def render_docfinal_artifacts(
    *,
    module_file: str | Path,
    template_path: str | Path | None,
    normalized_uri: str,
    context: dict[str, Any],
    chain: list[dict[str, Any]],
    sb: Any,
    render_docx: Callable[..., bytes],
    render_pdf: Callable[..., bytes],
    get_evidence: Callable[..., Any],
    build_zip: Callable[..., bytes],
) -> dict[str, Any]:
    resolved_template = Path(template_path).expanduser().resolve() if template_path else (
        Path(module_file).resolve().parent / "templates" / "rebar_inspection_table.docx"
    )

    docx_bytes = render_docx(template_path=resolved_template, context=context)
    pdf_bytes = render_pdf(docx_bytes=docx_bytes, context=context)

    evidence_items = None
    try:
        evidence_payload = get_evidence(sb=sb, boq_item_uri=normalized_uri)
        if isinstance(evidence_payload, dict) and isinstance(evidence_payload.get("evidence"), list):
            evidence_items = evidence_payload.get("evidence")
            context["evidence_count"] = len(evidence_items)
            context["evidence_source"] = "boq_chain"
    except Exception:
        evidence_items = None

    zip_bytes = build_zip(
        report_pdf_bytes=pdf_bytes,
        docx_bytes=docx_bytes,
        proof_chain=chain,
        context=context,
        evidence_items=evidence_items,
    )
    file_base = re.sub(r"[^\w\-]+", "_", normalized_uri, flags=re.ASCII)[:120] or "docfinal"

    return {
        "context": context,
        "docx_bytes": docx_bytes,
        "pdf_bytes": pdf_bytes,
        "zip_bytes": zip_bytes,
        "filename_base": file_base,
    }


__all__ = ["render_docfinal_artifacts"]

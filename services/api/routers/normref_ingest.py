"""NormRef ingest parser routes (P0)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from services.api.core import NormRefResolverService
from services.api.dependencies import get_normref_ingest_engine, get_normref_resolver
from services.api.domain.specir.runtime.normref_ingest import NormRefCandidatePatch, NormRefIngestEngine

router = APIRouter()


class CandidateStatusBody(BaseModel):
    job_id: str


class PublishBody(BaseModel):
    job_id: str
    candidate_ids: list[str] = Field(default_factory=list)
    version_tag: str = "latest"
    write_to_docs: bool = False


class CandidatePatchBody(BaseModel):
    job_id: str
    patch: NormRefCandidatePatch = Field(default_factory=NormRefCandidatePatch)


def _ensure_ok(result: dict[str, Any]) -> dict[str, Any]:
    if bool(result.get("ok")):
        return result
    error = str(result.get("error") or "request_failed")
    if error in {"job_not_found", "candidate_not_found"}:
        raise HTTPException(404, error)
    raise HTTPException(400, error)


@router.post("/upload")
async def upload_normref_document(
    file: UploadFile = File(...),
    std_code: str = Form(...),
    title: str = Form(""),
    level: str = Form("industry"),
    async_mode: bool = Form(False),
    engine: NormRefIngestEngine = Depends(get_normref_ingest_engine),
):
    content = await file.read()
    if not content:
        raise HTTPException(400, "file is empty")
    return _ensure_ok(
        engine.create_job(
            file_name=file.filename or "standard.pdf",
            content=content,
            std_code=std_code,
            title=title,
            level=level,
            defer_parse=bool(async_mode),
        )
    )


@router.get("/jobs/{job_id}")
async def get_ingest_job(
    job_id: str,
    engine: NormRefIngestEngine = Depends(get_normref_ingest_engine),
):
    return _ensure_ok(engine.get_job(job_id=job_id))


@router.get("/jobs/{job_id}/candidates")
async def list_ingest_candidates(
    job_id: str,
    status: str = "",
    engine: NormRefIngestEngine = Depends(get_normref_ingest_engine),
):
    return _ensure_ok(engine.list_candidates(job_id=job_id, status=status))


def _update_status(
    *,
    status: Literal["approved", "rejected"],
    candidate_id: str,
    body: CandidateStatusBody,
    engine: NormRefIngestEngine,
) -> dict[str, Any]:
    return _ensure_ok(
        engine.update_candidate_status(
            job_id=body.job_id,
            candidate_id=candidate_id,
            status=status,
        )
    )


@router.post("/candidates/{candidate_id}/approve")
async def approve_ingest_candidate(
    candidate_id: str,
    body: CandidateStatusBody,
    engine: NormRefIngestEngine = Depends(get_normref_ingest_engine),
):
    return _update_status(status="approved", candidate_id=candidate_id, body=body, engine=engine)


@router.post("/candidates/{candidate_id}/reject")
async def reject_ingest_candidate(
    candidate_id: str,
    body: CandidateStatusBody,
    engine: NormRefIngestEngine = Depends(get_normref_ingest_engine),
):
    return _update_status(status="rejected", candidate_id=candidate_id, body=body, engine=engine)


@router.post("/candidates/{candidate_id}/patch")
async def patch_ingest_candidate(
    candidate_id: str,
    body: CandidatePatchBody,
    engine: NormRefIngestEngine = Depends(get_normref_ingest_engine),
):
    return _ensure_ok(
        engine.patch_candidate(
            job_id=body.job_id,
            candidate_id=candidate_id,
            patch=body.patch,
        )
    )


@router.post("/publish")
async def publish_ingest_rules(
    body: PublishBody,
    engine: NormRefIngestEngine = Depends(get_normref_ingest_engine),
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    out = _ensure_ok(
        engine.publish(
            job_id=body.job_id,
            candidate_ids=body.candidate_ids,
            version_tag=body.version_tag,
            write_to_docs=bool(body.write_to_docs),
        ),
    )
    if bool(body.write_to_docs):
        refresh = resolver.refresh_rule_catalog()
        out["rule_catalog_count"] = int(refresh.get("count") or 0)
    return out

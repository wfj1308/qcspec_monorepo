"""SpecIR standard library routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from supabase import Client

from services.api.dependencies import get_supabase
from services.api.domain.specir import (
    get_specir_object,
    list_spu_library,
    resolve_spu_ref_pack,
    seed_specir_baseline,
)

router = APIRouter()


class SpecIRSeedBody(BaseModel):
    overwrite: bool = False
    include_full_spu: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/spu/library")
async def list_spu_standard_library(
    source: str = Query(default="all", description="builtin | registry | all"),
    industry: str = "",
    version: str = "",
    q: str = "",
    status: str = "active",
    limit: int = Query(default=200, ge=1, le=1000),
    sb: Client = Depends(get_supabase),
):
    return list_spu_library(
        sb=sb,
        source=source,
        industry=industry,
        version=version,
        q=q,
        status=status,
        limit=limit,
    )


@router.post("/spu/seed")
async def seed_spu_standard_library(
    body: SpecIRSeedBody,
    sb: Client = Depends(get_supabase),
):
    return seed_specir_baseline(
        sb=sb,
        overwrite=bool(body.overwrite),
        include_full_spu=bool(body.include_full_spu),
        metadata={"trigger": "api.specir.spu.seed", **(body.metadata or {})},
    )


@router.get("/object")
async def get_specir_registry_object(
    uri: str,
    sb: Client = Depends(get_supabase),
):
    return get_specir_object(sb=sb, uri=uri)


@router.get("/spu/resolve-ref")
async def resolve_spu_ref(
    item_code: str = "",
    item_name: str = "",
    quantity_unit: str = "",
    template_id: str = "",
):
    pack = resolve_spu_ref_pack(
        item_code=item_code,
        item_name=item_name,
        quantity_unit=quantity_unit,
        template_id=template_id,
    )
    return {
        "ok": True,
        "ref_spu_uri": pack.get("ref_spu_uri") or "",
        "ref_quota_uri": pack.get("ref_quota_uri") or "",
        "ref_meter_rule_uri": pack.get("ref_meter_rule_uri") or "",
    }

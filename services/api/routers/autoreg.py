"""
GitPeg auto-registration routes.

Provides minimal ERPNext -> backend -> Supabase autoreg flow:
- POST /v1/autoreg/project
- GET  /v1/autoreg/projects
- POST /v1/gitpeg/autoreg/project (alias)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from supabase import Client

from services.api.autoreg_service import (
    AutoRegisterProjectRequest,
    autoreg_project_flow,
    autoreg_projects_flow,
    normalize_request,
    upsert_autoreg,
)
from services.api.supabase_provider import get_supabase_client

router = APIRouter()


def get_supabase() -> Client:
    return get_supabase_client(
        url_envs=("GITPEG_SUPABASE_URL", "SUPABASE_URL"),
        key_envs=("GITPEG_SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY"),
        error_detail="supabase not configured for autoreg",
    )


# Backward-compatible exports used by other modules.
_normalize_request = normalize_request
_upsert_autoreg = upsert_autoreg


@router.post("/v1/autoreg/project")
async def autoreg_project(req: AutoRegisterProjectRequest, sb: Client = Depends(get_supabase)):
    return await autoreg_project_flow(req=req, sb=sb)


@router.post("/v1/gitpeg/autoreg/project")
async def autoreg_project_alias(req: AutoRegisterProjectRequest, sb: Client = Depends(get_supabase)):
    return await autoreg_project_flow(req=req, sb=sb)


@router.get("/v1/autoreg/projects")
async def autoreg_projects(
    limit: int = Query(default=100, ge=1, le=500),
    sb: Client = Depends(get_supabase),
):
    return autoreg_projects_flow(limit=limit, sb=sb)

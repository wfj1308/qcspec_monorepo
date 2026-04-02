"""
GitPeg auto-registration routes.

Provides minimal ERPNext -> backend -> Supabase autoreg flow:
- POST /v1/autoreg/project
- GET  /v1/autoreg/projects
- POST /v1/gitpeg/autoreg/project (alias)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from services.api.dependencies import get_autoreg_service
from services.api.domain import AutoregService
from services.api.domain.autoreg.helpers import AutoRegisterProjectRequest, _normalize_request, _upsert_autoreg

router = APIRouter()


@router.post("/v1/autoreg/project")
async def autoreg_project(req: AutoRegisterProjectRequest, autoreg_service: AutoregService = Depends(get_autoreg_service)):
    return await autoreg_service.autoreg_project(req=req)


@router.post("/v1/gitpeg/autoreg/project")
async def autoreg_project_alias(req: AutoRegisterProjectRequest, autoreg_service: AutoregService = Depends(get_autoreg_service)):
    return await autoreg_service.autoreg_project(req=req)


@router.get("/v1/autoreg/projects")
async def autoreg_projects(
    limit: int = Query(default=100, ge=1, le=500),
    autoreg_service: AutoregService = Depends(get_autoreg_service),
):
    return await autoreg_service.autoreg_projects(limit=limit)

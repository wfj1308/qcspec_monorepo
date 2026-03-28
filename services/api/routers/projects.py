"""
QCSpec project routes.
services/api/routers/projects.py
"""

from typing import Optional

from fastapi import APIRouter, Depends, Request
from supabase import Client

from services.api.projects_router_flow_service import (
    complete_project_gitpeg_registration_router_flow,
    create_project_router_flow,
    delete_project_flow,
    export_projects_csv_flow,
    get_project_flow,
    gitpeg_registrar_webhook_router_flow,
    list_activity_flow,
    list_projects_flow,
    sync_project_autoreg_endpoint_flow,
    update_project_flow,
)
from services.api.projects_schemas import (
    ProjectAutoregSyncRequest,
    ProjectCreate,
    ProjectGitPegCompleteRequest,
)
from services.api.dependencies import get_supabase

router = APIRouter()
public_router = APIRouter()


@router.get("/")
async def list_projects(
    enterprise_id: str,
    status: Optional[str] = None,
    type: Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    return list_projects_flow(
        enterprise_id=enterprise_id,
        status=status,
        project_type=type,
        sb=sb,
    )


@router.get("/activity")
async def list_activity(
    enterprise_id: str,
    limit: int = 20,
    sb: Client = Depends(get_supabase),
):
    return list_activity_flow(enterprise_id=enterprise_id, limit=limit, sb=sb)


@router.get("/export")
async def export_projects_csv(
    enterprise_id: str,
    status: Optional[str] = None,
    type: Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    return export_projects_csv_flow(
        enterprise_id=enterprise_id,
        status=status,
        project_type=type,
        sb=sb,
    )


@router.post("/", status_code=201)
async def create_project(
    body: ProjectCreate,
    sb: Client = Depends(get_supabase),
):
    return await create_project_router_flow(body=body, sb=sb)


@router.post("/{project_id}/autoreg-sync")
async def sync_project_autoreg(
    project_id: str,
    body: Optional[ProjectAutoregSyncRequest] = None,
    sb: Client = Depends(get_supabase),
):
    req = body or ProjectAutoregSyncRequest()
    return await sync_project_autoreg_endpoint_flow(project_id=project_id, body=req, sb=sb)


@router.post("/{project_id}/gitpeg/complete")
async def complete_project_gitpeg_registration(
    project_id: str,
    body: ProjectGitPegCompleteRequest,
    sb: Client = Depends(get_supabase),
):
    return await complete_project_gitpeg_registration_router_flow(
        project_id=project_id,
        body=body,
        sb=sb,
    )


@public_router.post("/gitpeg/webhook")
async def gitpeg_registrar_webhook(
    request: Request,
    sb: Client = Depends(get_supabase),
):
    return await gitpeg_registrar_webhook_router_flow(request=request, sb=sb)


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    sb: Client = Depends(get_supabase),
):
    return get_project_flow(project_id=project_id, sb=sb)


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    updates: dict,
    sb: Client = Depends(get_supabase),
):
    return update_project_flow(project_id=project_id, updates=updates, sb=sb)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    enterprise_id: Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    return delete_project_flow(project_id=project_id, enterprise_id=enterprise_id, sb=sb)

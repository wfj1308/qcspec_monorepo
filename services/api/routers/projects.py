"""
QCSpec project routes.
services/api/routers/projects.py
"""

from typing import Optional

from fastapi import APIRouter, Depends, Request

from services.api.dependencies import get_projects_service
from services.api.domain import ProjectsService
from services.api.projects_schemas import ProjectAutoregSyncRequest, ProjectCreate, ProjectGitPegCompleteRequest

router = APIRouter()
public_router = APIRouter()


@router.get("/")
async def list_projects(
    enterprise_id: str,
    status: Optional[str] = None,
    type: Optional[str] = None,
    projects_service: ProjectsService = Depends(get_projects_service),
):
    return await projects_service.list_projects(
        enterprise_id=enterprise_id,
        status=status,
        project_type=type,
    )


@router.get("/activity")
async def list_activity(
    enterprise_id: str,
    limit: int = 20,
    projects_service: ProjectsService = Depends(get_projects_service),
):
    return await projects_service.list_activity(enterprise_id=enterprise_id, limit=limit)


@router.get("/export")
async def export_projects_csv(
    enterprise_id: str,
    status: Optional[str] = None,
    type: Optional[str] = None,
    projects_service: ProjectsService = Depends(get_projects_service),
):
    return await projects_service.export_projects_csv(
        enterprise_id=enterprise_id,
        status=status,
        project_type=type,
    )


@router.post("/", status_code=201)
async def create_project(
    body: ProjectCreate,
    projects_service: ProjectsService = Depends(get_projects_service),
):
    return await projects_service.create_project(body=body)


@router.post("/{project_id}/autoreg-sync")
async def sync_project_autoreg(
    project_id: str,
    body: Optional[ProjectAutoregSyncRequest] = None,
    projects_service: ProjectsService = Depends(get_projects_service),
):
    req = body or ProjectAutoregSyncRequest()
    return await projects_service.sync_project_autoreg(project_id=project_id, body=req)


@router.post("/{project_id}/gitpeg/complete")
async def complete_project_gitpeg_registration(
    project_id: str,
    body: ProjectGitPegCompleteRequest,
    projects_service: ProjectsService = Depends(get_projects_service),
):
    return await projects_service.complete_project_gitpeg_registration(
        project_id=project_id,
        body=body,
    )


@public_router.post("/gitpeg/webhook")
async def gitpeg_registrar_webhook(
    request: Request,
    projects_service: ProjectsService = Depends(get_projects_service),
):
    return await projects_service.gitpeg_registrar_webhook(request=request)


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    projects_service: ProjectsService = Depends(get_projects_service),
):
    return await projects_service.get_project(project_id=project_id)


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    updates: dict,
    projects_service: ProjectsService = Depends(get_projects_service),
):
    return await projects_service.update_project(project_id=project_id, updates=updates)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    enterprise_id: Optional[str] = None,
    projects_service: ProjectsService = Depends(get_projects_service),
):
    return await projects_service.delete_project(project_id=project_id, enterprise_id=enterprise_id)

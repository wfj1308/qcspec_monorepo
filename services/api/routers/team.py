"""
Team management routes for QCSpec.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from services.api.dependencies import get_team_service
from services.api.domain import TeamService

router = APIRouter()


class MemberCreate(BaseModel):
    enterprise_id: str
    name: str
    email: str
    dto_role: str = "AI"
    title: Optional[str] = None
    project_ids: list[str] = Field(default_factory=list)


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    dto_role: Optional[str] = None
    title: Optional[str] = None
    project_ids: Optional[list[str]] = None
    is_active: Optional[bool] = None


@router.get("/members")
async def list_members(
    enterprise_id: str,
    include_inactive: bool = False,
    team_service: TeamService = Depends(get_team_service),
):
    return await team_service.list_members(enterprise_id=enterprise_id, include_inactive=include_inactive)


@router.post("/members", status_code=201)
async def create_member(body: MemberCreate, team_service: TeamService = Depends(get_team_service)):
    return await team_service.create_member(body=body)


@router.patch("/members/{user_id}")
async def update_member(user_id: str, body: MemberUpdate, team_service: TeamService = Depends(get_team_service)):
    return await team_service.update_member(user_id=user_id, body=body)


@router.delete("/members/{user_id}")
async def remove_member(user_id: str, team_service: TeamService = Depends(get_team_service)):
    return await team_service.remove_member(user_id=user_id)

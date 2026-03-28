"""
Team management routes for QCSpec.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import Client

from services.api.dependencies import get_supabase
from services.api.team_flow_service import (
    create_member_flow,
    list_members_flow,
    remove_member_flow,
    update_member_flow,
)

router = APIRouter()


class MemberCreate(BaseModel):
    enterprise_id: str
    name: str
    email: str
    dto_role: str = "AI"
    title: Optional[str] = None
    project_ids: list[str] = []


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
    sb: Client = Depends(get_supabase),
):
    return list_members_flow(enterprise_id=enterprise_id, include_inactive=include_inactive, sb=sb)


@router.post("/members", status_code=201)
async def create_member(body: MemberCreate, sb: Client = Depends(get_supabase)):
    return create_member_flow(body=body, sb=sb)


@router.patch("/members/{user_id}")
async def update_member(user_id: str, body: MemberUpdate, sb: Client = Depends(get_supabase)):
    return update_member_flow(user_id=user_id, body=body, sb=sb)


@router.delete("/members/{user_id}")
async def remove_member(user_id: str, sb: Client = Depends(get_supabase)):
    return remove_member_flow(user_id=user_id, sb=sb)

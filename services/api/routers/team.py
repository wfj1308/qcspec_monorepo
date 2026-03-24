"""
Team management routes for QCSpec.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import Client, create_client

router = APIRouter()

@lru_cache(maxsize=1)
def _supabase_client_cached(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase() -> Client:
    url = str(os.getenv("SUPABASE_URL") or "").strip()
    key = str(os.getenv("SUPABASE_SERVICE_KEY") or "").strip()
    if not url or not key:
        raise HTTPException(500, "Supabase not configured")
    return _supabase_client_cached(url, key)


ROLE_SET = {"PUBLIC", "AI", "SUPERVISOR", "OWNER", "REGULATOR", "MARKET"}


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "", name.strip()).lower()
    return slug[:32] or "member"


def _normalize_role(role: str) -> str:
    r = (role or "").upper()
    if r not in ROLE_SET:
        raise HTTPException(400, "invalid dto_role")
    return r


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


def _projects_by_user(sb: Client, user_ids: list[str]) -> dict[str, list[str]]:
    if not user_ids:
        return {}
    rel = sb.table("project_members").select("user_id,project_id").in_("user_id", user_ids).execute()
    mapping: dict[str, list[str]] = {uid: [] for uid in user_ids}
    for row in (rel.data or []):
        uid = row.get("user_id")
        pid = row.get("project_id")
        if uid in mapping and pid:
            mapping[uid].append(pid)
    return mapping


@router.get("/members")
async def list_members(
    enterprise_id: str,
    include_inactive: bool = False,
    sb: Client = Depends(get_supabase),
):
    q = sb.table("users").select("id,name,email,title,dto_role,is_active,v_uri,created_at").eq("enterprise_id", enterprise_id)
    if not include_inactive:
        q = q.eq("is_active", True)
    res = q.order("created_at", desc=False).execute()
    rows = res.data or []
    uid_list = [r["id"] for r in rows if r.get("id")]
    proj_map = _projects_by_user(sb, uid_list)
    data = []
    for r in rows:
        uid = r["id"]
        data.append({
            **r,
            "projects": proj_map.get(uid, []),
        })
    return {"data": data}


@router.post("/members", status_code=201)
async def create_member(body: MemberCreate, sb: Client = Depends(get_supabase)):
    role = _normalize_role(body.dto_role)
    ent = sb.table("enterprises").select("id,v_uri").eq("id", body.enterprise_id).single().execute()
    if not ent.data:
        raise HTTPException(404, "enterprise not found")

    ent_uri = ent.data["v_uri"]
    existing = sb.table("users").select("id,enterprise_id").eq("email", body.email).limit(1).execute()
    user_id: Optional[str] = None

    if existing.data:
        ex = existing.data[0]
        if ex["enterprise_id"] != body.enterprise_id:
            raise HTTPException(409, "email already exists in another enterprise")
        upd = sb.table("users").update({
            "name": body.name,
            "title": body.title,
            "dto_role": role,
            "is_active": True,
        }).eq("id", ex["id"]).execute()
        if not upd.data:
            raise HTTPException(500, "failed to update member")
        user_id = ex["id"]
    else:
        member_uri = f"{ent_uri}executor/{_slugify(body.name)}/"
        ins = sb.table("users").insert({
            "enterprise_id": body.enterprise_id,
            "v_uri": member_uri,
            "name": body.name,
            "email": body.email,
            "dto_role": role,
            "title": body.title,
            "is_active": True,
        }).execute()
        if not ins.data:
            raise HTTPException(500, "failed to create member")
        user_id = ins.data[0]["id"]

    if body.project_ids:
        # Replace project memberships with incoming list.
        sb.table("project_members").delete().eq("user_id", user_id).execute()
        rel_rows = [{"project_id": pid, "user_id": user_id, "dto_role": role} for pid in body.project_ids]
        sb.table("project_members").insert(rel_rows).execute()

    user = sb.table("users").select("id,name,email,title,dto_role,is_active,v_uri,created_at").eq("id", user_id).single().execute()
    data = user.data or {}
    data["projects"] = body.project_ids
    return {"data": data}


@router.patch("/members/{user_id}")
async def update_member(user_id: str, body: MemberUpdate, sb: Client = Depends(get_supabase)):
    updates: dict = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.email is not None:
        updates["email"] = body.email
    if body.title is not None:
        updates["title"] = body.title
    if body.dto_role is not None:
        updates["dto_role"] = _normalize_role(body.dto_role)
    if body.is_active is not None:
        updates["is_active"] = body.is_active

    if updates:
        res = sb.table("users").update(updates).eq("id", user_id).execute()
        if not res.data:
            raise HTTPException(404, "member not found")

    if body.project_ids is not None:
        # Role in project defaults to global role if provided, otherwise keep OWNER fallback.
        role = updates.get("dto_role")
        if role is None:
            cur = sb.table("users").select("dto_role").eq("id", user_id).single().execute()
            role = (cur.data or {}).get("dto_role", "OWNER")
        sb.table("project_members").delete().eq("user_id", user_id).execute()
        if body.project_ids:
            rel_rows = [{"project_id": pid, "user_id": user_id, "dto_role": role} for pid in body.project_ids]
            sb.table("project_members").insert(rel_rows).execute()

    user = sb.table("users").select("id,name,email,title,dto_role,is_active,v_uri,created_at").eq("id", user_id).single().execute()
    if not user.data:
        raise HTTPException(404, "member not found")
    proj_map = _projects_by_user(sb, [user_id])
    data = user.data
    data["projects"] = proj_map.get(user_id, [])
    return {"data": data}


@router.delete("/members/{user_id}")
async def remove_member(user_id: str, sb: Client = Depends(get_supabase)):
    sb.table("project_members").delete().eq("user_id", user_id).execute()
    res = sb.table("users").update({"is_active": False}).eq("id", user_id).execute()
    if not res.data:
        raise HTTPException(404, "member not found")
    return {"ok": True}

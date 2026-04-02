"""Canonical team-domain flow entry points."""

from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException
from supabase import Client

ROLE_SET = {"PUBLIC", "AI", "SUPERVISOR", "OWNER", "REGULATOR", "MARKET"}


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "", name.strip()).lower()
    return slug[:32] or "member"


def _normalize_role(role: str) -> str:
    r = (role or "").upper()
    if r not in ROLE_SET:
        raise HTTPException(400, "invalid dto_role")
    return r


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


def list_members_flow(*, enterprise_id: str, include_inactive: bool, sb: Client) -> dict[str, Any]:
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


def create_member_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    role = _normalize_role(body.dto_role)
    ent = sb.table("enterprises").select("id,v_uri").eq("id", body.enterprise_id).single().execute()
    if not ent.data:
        raise HTTPException(404, "enterprise not found")

    ent_uri = ent.data["v_uri"]
    existing = sb.table("users").select("id,enterprise_id").eq("email", body.email).limit(1).execute()

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
        sb.table("project_members").delete().eq("user_id", user_id).execute()
        rel_rows = [{"project_id": pid, "user_id": user_id, "dto_role": role} for pid in body.project_ids]
        sb.table("project_members").insert(rel_rows).execute()

    user = sb.table("users").select("id,name,email,title,dto_role,is_active,v_uri,created_at").eq("id", user_id).single().execute()
    data = user.data or {}
    data["projects"] = body.project_ids
    return {"data": data}


def update_member_flow(*, user_id: str, body: Any, sb: Client) -> dict[str, Any]:
    updates: dict[str, Any] = {}
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


def remove_member_flow(*, user_id: str, sb: Client) -> dict[str, Any]:
    sb.table("project_members").delete().eq("user_id", user_id).execute()
    res = sb.table("users").update({"is_active": False}).eq("id", user_id).execute()
    if not res.data:
        raise HTTPException(404, "member not found")
    return {"ok": True}


__all__ = [
    "list_members_flow",
    "create_member_flow",
    "update_member_flow",
    "remove_member_flow",
]

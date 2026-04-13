"""DTORole upstream proxy routes.

This router keeps frontend calls on QCSpec backend while delegating DTORole
read/write operations to teammate-owned APIs.
"""

from __future__ import annotations

import json
import os
from typing import Final

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter()

UPSTREAM_BASE_URL = os.getenv("DTOROLE_UPSTREAM_BASE_URL", "").strip().rstrip("/")
UPSTREAM_BEARER_TOKEN = os.getenv("DTOROLE_UPSTREAM_BEARER_TOKEN", "").strip()
UPSTREAM_API_KEY = os.getenv("DTOROLE_UPSTREAM_API_KEY", "").strip()
REQUEST_TIMEOUT_S = float(os.getenv("DTOROLE_PROXY_TIMEOUT_S", "12"))

FORWARDED_HEADER_KEYS: Final[tuple[str, ...]] = (
    "authorization",
    "x-request-id",
    "x-actor-role",
    "x-actor-name",
    "x-trace-id",
)


def _build_upstream_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key in FORWARDED_HEADER_KEYS:
        value = request.headers.get(key)
        if value:
            headers[key] = value
    if UPSTREAM_BEARER_TOKEN:
        headers["authorization"] = f"Bearer {UPSTREAM_BEARER_TOKEN}"
    if UPSTREAM_API_KEY:
        headers["x-api-key"] = UPSTREAM_API_KEY
    return headers


async def _proxy(
    request: Request,
    *,
    method: str,
    upstream_path: str,
    include_body: bool,
) -> Response:
    if not UPSTREAM_BASE_URL:
        raise HTTPException(
            status_code=503,
            detail="DTOROLE_UPSTREAM_BASE_URL not configured",
        )

    query = request.url.query
    url = f"{UPSTREAM_BASE_URL}{upstream_path}"
    if query:
        url = f"{url}?{query}"

    body = await request.body() if include_body else None
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S) as client:
            upstream = await client.request(
                method=method,
                url=url,
                content=body,
                headers=_build_upstream_headers(request),
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="DTORole upstream timeout") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="DTORole upstream unavailable") from exc

    content_type = upstream.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = upstream.json()
        except json.JSONDecodeError:
            payload = {"detail": upstream.text or "upstream returned invalid json"}
        return Response(
            status_code=upstream.status_code,
            content=json.dumps(payload, ensure_ascii=False),
            media_type="application/json",
        )

    return Response(
        status_code=upstream.status_code,
        content=upstream.content,
        media_type=content_type or None,
    )


@router.get("/permission-check")
async def permission_check(request: Request) -> Response:
    return await _proxy(
        request,
        method="GET",
        upstream_path="/api/v1/dtorole/permission-check",
        include_body=False,
    )


@router.get("/role-bindings")
async def list_role_bindings(request: Request) -> Response:
    return await _proxy(
        request,
        method="GET",
        upstream_path="/api/v1/dtorole/role-bindings",
        include_body=False,
    )


@router.post("/role-bindings")
async def save_role_binding(request: Request) -> Response:
    return await _proxy(
        request,
        method="POST",
        upstream_path="/api/v1/dtorole/role-bindings",
        include_body=True,
    )


@router.get("/roles")
async def list_roles(request: Request) -> Response:
    return await _proxy(
        request,
        method="GET",
        upstream_path="/api/v1/dtorole/roles",
        include_body=False,
    )


@router.post("/roles")
async def create_role(request: Request) -> Response:
    return await _proxy(
        request,
        method="POST",
        upstream_path="/api/v1/dtorole/roles",
        include_body=True,
    )


@router.patch("/roles/{role_id}")
async def update_role(role_id: str, request: Request) -> Response:
    return await _proxy(
        request,
        method="PATCH",
        upstream_path=f"/api/v1/dtorole/roles/{role_id}",
        include_body=True,
    )


@router.delete("/roles/{role_id}")
async def delete_role(role_id: str, request: Request) -> Response:
    return await _proxy(
        request,
        method="DELETE",
        upstream_path=f"/api/v1/dtorole/roles/{role_id}",
        include_body=False,
    )


@router.get("/templates")
async def list_templates(request: Request) -> Response:
    return await _proxy(
        request,
        method="GET",
        upstream_path="/api/v1/dtorole/templates",
        include_body=False,
    )

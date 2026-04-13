"""File upload proxy routes.

This keeps frontend uploads on the QCSpec backend while forwarding the
actual file storage call to teammate-owned API endpoints.
"""

from __future__ import annotations

import json
import os
from typing import Final

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter()

UPSTREAM_BASE_URL = (
    os.getenv("UPLOAD_UPSTREAM_BASE_URL", "").strip().rstrip("/")
    or os.getenv("DTOROLE_UPSTREAM_BASE_URL", "").strip().rstrip("/")
)
UPSTREAM_BEARER_TOKEN = os.getenv("UPLOAD_UPSTREAM_BEARER_TOKEN", "").strip()
UPSTREAM_API_KEY = os.getenv("UPLOAD_UPSTREAM_API_KEY", "").strip()
REQUEST_TIMEOUT_S = float(os.getenv("UPLOAD_PROXY_TIMEOUT_S", "20"))

FORWARDED_HEADER_KEYS: Final[tuple[str, ...]] = (
    "authorization",
    "x-request-id",
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


async def _proxy_upload(request: Request, *, upstream_path: str) -> Response:
    if not UPSTREAM_BASE_URL:
        raise HTTPException(
            status_code=503,
            detail="UPLOAD_UPSTREAM_BASE_URL not configured",
        )

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty upload body")

    url = f"{UPSTREAM_BASE_URL}{upstream_path}"
    content_type = request.headers.get("content-type")
    headers = _build_upstream_headers(request)
    if content_type:
        headers["content-type"] = content_type

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S) as client:
            upstream = await client.post(url=url, content=body, headers=headers)
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="upload upstream timeout") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="upload upstream unavailable") from exc

    upstream_content_type = upstream.headers.get("content-type", "")
    if "application/json" in upstream_content_type:
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
        media_type=upstream_content_type or None,
    )


@router.post("/upload")
async def upload_alias(request: Request) -> Response:
    return await _proxy_upload(request, upstream_path="/upload")


@router.post("/api/v1/files/upload")
async def upload_v1_files(request: Request) -> Response:
    return await _proxy_upload(request, upstream_path="/api/v1/files/upload")


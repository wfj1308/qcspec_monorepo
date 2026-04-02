"""HTTP/transport utilities shared by API flow modules."""

from __future__ import annotations

import io

from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse


def validate_upload_content(
    content: bytes,
    *,
    max_bytes: int,
    empty_error: str = "empty upload file",
    too_large_error: str | None = None,
) -> bytes:
    if not content:
        raise HTTPException(400, empty_error)
    if len(content) > max_bytes:
        detail = too_large_error or f"upload file too large, max {max_bytes // (1024 * 1024)}MB"
        raise HTTPException(400, detail)
    return content


def read_upload_content_sync(
    *,
    file: UploadFile,
    max_bytes: int,
    empty_error: str = "empty upload file",
    too_large_error: str | None = None,
) -> bytes:
    content = file.file.read()
    return validate_upload_content(
        content,
        max_bytes=max_bytes,
        empty_error=empty_error,
        too_large_error=too_large_error,
    )


async def read_upload_content_async(
    *,
    file: UploadFile,
    max_bytes: int,
    empty_error: str = "empty file",
    too_large_error: str | None = None,
) -> bytes:
    content = await file.read()
    return validate_upload_content(
        content,
        max_bytes=max_bytes,
        empty_error=empty_error,
        too_large_error=too_large_error,
    )


def binary_download_response(
    *,
    payload: bytes,
    media_type: str,
    filename: str,
    headers: dict[str, str] | None = None,
) -> StreamingResponse:
    out_headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if headers:
        out_headers.update(headers)
    return StreamingResponse(io.BytesIO(payload or b""), media_type=media_type, headers=out_headers)

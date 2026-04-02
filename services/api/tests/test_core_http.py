from __future__ import annotations

import asyncio
import io

import pytest
from fastapi import HTTPException, UploadFile

from services.api.core.http import (
    binary_download_response,
    read_upload_content_async,
    read_upload_content_sync,
    validate_upload_content,
)


def test_validate_upload_content_success() -> None:
    data = b"abc"
    assert validate_upload_content(data, max_bytes=10) == data


def test_validate_upload_content_raises_for_empty() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_upload_content(b"", max_bytes=10)
    assert exc.value.status_code == 400
    assert exc.value.detail == "empty upload file"


def test_validate_upload_content_raises_for_size_limit() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_upload_content(b"123456", max_bytes=5, too_large_error="too large")
    assert exc.value.status_code == 400
    assert exc.value.detail == "too large"


def test_read_upload_content_sync_reads_from_upload_file() -> None:
    upload = UploadFile(filename="a.txt", file=io.BytesIO(b"sync-bytes"))
    assert read_upload_content_sync(file=upload, max_bytes=20) == b"sync-bytes"


def test_read_upload_content_async_reads_from_upload_file() -> None:
    upload = UploadFile(filename="a.txt", file=io.BytesIO(b"async-bytes"))
    content = asyncio.run(read_upload_content_async(file=upload, max_bytes=20))
    assert content == b"async-bytes"


def test_binary_download_response_sets_headers() -> None:
    response = binary_download_response(
        payload=b"hello",
        media_type="application/octet-stream",
        filename="demo.bin",
        headers={"Cache-Control": "no-store"},
    )
    assert response.headers["content-disposition"] == 'attachment; filename="demo.bin"'
    assert response.headers["cache-control"] == "no-store"

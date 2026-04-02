from __future__ import annotations

import hashlib

import pytest
from fastapi import HTTPException

from services.api.domain.execution.triprole_docfinal_finalize import finalize_master_docfinal


def test_finalize_master_docfinal_raises_for_empty_bytes() -> None:
    with pytest.raises(HTTPException) as exc:
        finalize_master_docfinal(
            master_bytes=b"",
            project_uri="v://project/demo",
            project_name="Demo",
            exported_items=[],
            item_errors=[],
            passphrase="",
            utc_iso=lambda: "2026-04-02T00:00:00Z",
            encrypt_aes256=lambda *_: {},
            create_birth_row=lambda *_: {},
        )
    assert exc.value.status_code == 500


def test_finalize_master_docfinal_success() -> None:
    calls: dict[str, object] = {}

    def _create_birth_row(
        proof_id: str,
        owner_uri: str,
        project_uri: str,
        birth_state: dict,
        segment_uri: str,
    ) -> dict:
        calls["proof_id"] = proof_id
        calls["owner_uri"] = owner_uri
        calls["project_uri"] = project_uri
        calls["birth_state"] = birth_state
        calls["segment_uri"] = segment_uri
        return {
            "proof_id": proof_id,
            "proof_hash": "hash-x",
            "gitpeg_anchor": "anchor-x",
        }

    payload = finalize_master_docfinal(
        master_bytes=b"abc",
        project_uri="v://project/demo",
        project_name="Demo",
        exported_items=[{"id": 1}],
        item_errors=[{"err": 1}],
        passphrase="",
        utc_iso=lambda: "2026-04-02T00:00:00Z",
        encrypt_aes256=lambda content, secret: {
            "algorithm": "AES-256-GCM",
            "cipher_hash": hashlib.sha256(content + secret.encode("utf-8")).hexdigest(),
        },
        create_birth_row=_create_birth_row,
    )

    expected_root = hashlib.sha256(b"abc").hexdigest()
    assert payload["root_hash"] == expected_root
    assert payload["filename"] == f"MASTER-DSP-{expected_root[:16]}.qcdsp"
    assert payload["birth_certificate"]["proof_hash"] == "hash-x"  # type: ignore[index]
    assert payload["birth_certificate"]["gitpeg_anchor"] == "anchor-x"  # type: ignore[index]
    assert isinstance(payload["encrypted_bytes"], bytes)
    assert calls["proof_id"] == f"GP-DOCFINAL-{expected_root[:16].upper()}"
    assert calls["owner_uri"] == "v://project/demo/executor/system/"
    assert calls["project_uri"] == "v://project/demo"
    assert calls["segment_uri"] == "v://project/demo/docfinal/master"
    assert calls["birth_state"]["item_count"] == 1  # type: ignore[index]
    assert calls["birth_state"]["error_count"] == 1  # type: ignore[index]

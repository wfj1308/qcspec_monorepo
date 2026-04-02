"""DocFinal master package finalization helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from fastapi import HTTPException


def finalize_master_docfinal(
    *,
    master_bytes: bytes,
    project_uri: str,
    project_name: str,
    exported_items: list[dict[str, Any]],
    item_errors: list[dict[str, Any]],
    passphrase: str,
    utc_iso: Callable[[], str],
    encrypt_aes256: Callable[[bytes, str], dict[str, Any]],
    create_birth_row: Callable[[str, str, str, dict[str, Any], str], dict[str, Any]],
) -> dict[str, Any]:
    if not master_bytes:
        raise HTTPException(500, "master docfinal package generation failed")

    normalized_project_uri = str(project_uri or "")
    normalized_project_name = str(project_name or "")

    root_hash = hashlib.sha256(master_bytes).hexdigest()
    encrypted = encrypt_aes256(master_bytes, passphrase or root_hash)

    proof_id = f"GP-DOCFINAL-{root_hash[:16].upper()}"
    owner_uri = f"{normalized_project_uri.rstrip('/')}/executor/system/"
    segment_uri = f"{normalized_project_uri.rstrip('/')}/docfinal/master"
    generated_at = utc_iso()
    birth_state = {
        "artifact_type": "docfinal_master_dsp",
        "project_uri": normalized_project_uri,
        "project_name": normalized_project_name,
        "root_hash": root_hash,
        "encryption": {
            "algorithm": encrypted.get("algorithm"),
            "cipher_hash": encrypted.get("cipher_hash"),
        },
        "item_count": len(exported_items),
        "error_count": len(item_errors),
        "generated_at": generated_at,
    }

    birth_row = create_birth_row(proof_id, owner_uri, normalized_project_uri, birth_state, segment_uri)

    certificate = {
        "proof_id": str((birth_row or {}).get("proof_id") or ""),
        "proof_hash": str((birth_row or {}).get("proof_hash") or ""),
        "gitpeg_anchor": str((birth_row or {}).get("gitpeg_anchor") or ""),
        "project_uri": normalized_project_uri,
        "root_hash": root_hash,
        "artifact_uri": f"{normalized_project_uri.rstrip('/')}/docfinal/master/{root_hash[:16]}",
    }

    encrypted_blob = json.dumps(
        {
            "meta": {
                "format": "QCSpec-Master-DSP-Encrypted",
                "version": "1.0",
                "project_uri": normalized_project_uri,
                "project_name": normalized_project_name,
                "root_hash": root_hash,
            },
            "encryption": encrypted,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    ).encode("utf-8")

    return {
        "root_hash": root_hash,
        "birth_certificate": certificate,
        "encrypted_bytes": encrypted_blob,
        "filename": f"MASTER-DSP-{root_hash[:16]}.qcdsp",
    }


__all__ = ["finalize_master_docfinal"]

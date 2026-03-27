"""
QCSpec media evidence routes.
services/api/routers/photos.py
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import hashlib
import json
import os
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from supabase import Client, create_client

from .proof_utxo_engine import ProofUTXOEngine

router = APIRouter()


@lru_cache(maxsize=1)
def _supabase_client_cached(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase() -> Client:
    url = str(os.getenv("SUPABASE_URL") or "").strip()
    key = str(
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    ).strip()
    if not url or not key:
        raise HTTPException(500, "Supabase not configured")
    return _supabase_client_cached(url, key)


def _gen_proof(v_uri: str, data: dict[str, Any]) -> str:
    payload = json.dumps(
        {
            "uri": v_uri,
            "data": data,
            "ts": datetime.utcnow().isoformat(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()
    return f"GP-PROOF-{h}"


def _guess_owner_uri(project_uri: str) -> str:
    root = str(project_uri or "").strip()
    for marker in ("/highway/", "/bridge/", "/urban/", "/road/", "/tunnel/"):
        idx = root.find(marker)
        if idx > 0:
            root = root[: idx + 1]
            break
    if not root.endswith("/"):
        root += "/"
    return f"{root}executor/system/"


def _media_kind(content_type: str, file_name: str) -> str:
    ctype = str(content_type or "").lower()
    if ctype.startswith("image/"):
        return "image"
    if ctype.startswith("video/"):
        return "video"
    lower_name = str(file_name or "").lower()
    if lower_name.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic")):
        return "image"
    if lower_name.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")):
        return "video"
    return "file"


@router.post("/upload", status_code=201)
async def upload_photo(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    enterprise_id: str = Form(...),
    location: Optional[str] = Form(None),
    inspection_id: Optional[str] = Form(None),
    gps_lat: Optional[float] = Form(None),
    gps_lng: Optional[float] = Form(None),
    sb: Client = Depends(get_supabase),
):
    """
    Upload media evidence and generate linked Proof record.
    Backward compatible route name: /v1/photos/upload
    """
    content_type = str(file.content_type or "").strip().lower()
    kind = _media_kind(content_type, file.filename or "")
    if kind not in {"image", "video"}:
        raise HTTPException(400, "Only image/video files are supported")

    content = await file.read()
    size = len(content)
    limit = 20 * 1024 * 1024 if kind == "image" else 200 * 1024 * 1024
    if size > limit:
        raise HTTPException(400, f"File too large, max {limit // (1024 * 1024)}MB")

    evidence_hash = hashlib.sha256(content).hexdigest()

    proj = sb.table("projects").select("v_uri").eq("id", project_id).single().execute()
    if not proj.data:
        raise HTTPException(404, "Project not found")

    proj_uri = str(proj.data.get("v_uri") or "")
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = str(file.filename or "evidence.bin").replace("\\", "_").replace("/", "_")
    storage_path = f"{enterprise_id}/{project_id}/{ts}_{safe_name}"

    sb.storage.from_("qcspec-photos").upload(
        storage_path,
        content,
        file_options={"content-type": content_type or "application/octet-stream"},
    )
    public_url = sb.storage.from_("qcspec-photos").get_public_url(storage_path)
    public_url_text = public_url if isinstance(public_url, str) else ""

    taken_at = datetime.utcnow().isoformat()
    photo_res = sb.table("photos").insert(
        {
            "project_id": project_id,
            "enterprise_id": enterprise_id,
            "inspection_id": inspection_id,
            "file_name": safe_name,
            "storage_path": storage_path,
            "storage_url": public_url_text,
            "location": location,
            "gps_lat": gps_lat,
            "gps_lng": gps_lng,
            "file_size": size,
            "taken_at": taken_at,
        }
    ).execute()
    if not photo_res.data:
        raise HTTPException(500, "Failed to save media record")

    photo = photo_res.data[0]
    photo_id = str(photo.get("id"))
    v_uri = f"{proj_uri}photo/{photo_id}/"
    proof_id = _gen_proof(
        v_uri,
        {
            "file": safe_name,
            "location": location,
            "inspection_id": inspection_id,
            "evidence_hash": evidence_hash,
            "content_type": content_type,
        },
    )

    update_payload = {
        "v_uri": v_uri,
        "proof_id": proof_id,
        "proof_hash": proof_id.replace("GP-PROOF-", "").lower(),
    }
    sb.table("photos").update(update_payload).eq("id", photo_id).execute()

    # Optional columns for newer schemas.
    try:
        sb.table("photos").update(
            {
                "evidence_hash": evidence_hash,
                "content_type": content_type,
            }
        ).eq("id", photo_id).execute()
    except Exception:
        pass

    safe_location = (location or "").strip() or "UnknownStake"
    sb.table("proof_chain").insert(
        {
            "proof_id": proof_id,
            "proof_hash": proof_id.replace("GP-PROOF-", "").lower(),
            "enterprise_id": enterprise_id,
            "project_id": project_id,
            "v_uri": v_uri,
            "object_type": "photo",
            "object_id": photo_id,
            "action": "upload",
            "summary": f"media_upload|{kind}|{safe_location}|{safe_name}",
            "status": "confirmed",
        }
    ).execute()

    try:
        ProofUTXOEngine(sb).create(
            proof_id=proof_id,
            owner_uri=_guess_owner_uri(proj_uri),
            project_id=project_id,
            project_uri=proj_uri,
            proof_type="photo",
            result="PASS",
            state_data={
                "photo_id": photo_id,
                "v_uri": v_uri,
                "file_name": safe_name,
                "media_type": kind,
                "content_type": content_type,
                "location": location,
                "inspection_id": inspection_id,
                "storage_path": storage_path,
                "storage_url": public_url_text,
                "gps_lat": gps_lat,
                "gps_lng": gps_lng,
                "evidence_hash": evidence_hash,
                "evidence_hashes": [evidence_hash],
                "taken_at": taken_at,
            },
            signer_uri=_guess_owner_uri(proj_uri),
            signer_role="AI",
            conditions=[],
            parent_proof_id=None,
            norm_uri=None,
        )
    except Exception:
        # Keep old flow running if proof_utxo migration has not been applied yet.
        pass

    return {
        "photo_id": photo_id,
        "v_uri": v_uri,
        "proof_id": proof_id,
        "storage_url": public_url_text,
        "location": location,
        "media_type": kind,
        "content_type": content_type,
        "evidence_hash": evidence_hash,
    }


@router.get("/")
async def list_photos(
    project_id: str,
    inspection_id: Optional[str] = None,
    limit: int = 50,
    sb: Client = Depends(get_supabase),
):
    q = (
        sb.table("photos")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if inspection_id:
        q = q.eq("inspection_id", inspection_id)
    res = q.execute()
    rows = res.data or []
    return {"data": rows, "count": len(rows)}


@router.delete("/{photo_id}")
async def delete_photo(photo_id: str, sb: Client = Depends(get_supabase)):
    photo = sb.table("photos").select("storage_path,proof_id").eq("id", photo_id).single().execute()
    if photo.data:
        try:
            sb.storage.from_("qcspec-photos").remove([photo.data["storage_path"]])
        except Exception:
            pass
        try:
            sb.table("proof_chain").delete().eq("object_type", "photo").eq("object_id", photo_id).execute()
            if photo.data.get("proof_id"):
                sb.table("proof_chain").delete().eq("proof_id", photo.data["proof_id"]).execute()
        except Exception:
            pass
    sb.table("photos").delete().eq("id", photo_id).execute()
    return {"ok": True}

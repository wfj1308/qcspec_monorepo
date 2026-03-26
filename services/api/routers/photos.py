"""
QCSpec · 照片路由
services/api/routers/photos.py
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
from supabase import create_client, Client
from datetime import datetime
import os, hashlib, json
from .proof_utxo_engine import ProofUTXOEngine

router = APIRouter()

def get_supabase() -> Client:
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )

def _gen_proof(v_uri: str, data: dict) -> str:
    payload = json.dumps({"uri": v_uri, "data": data,
        "ts": datetime.utcnow().isoformat()}, sort_keys=True)
    h = hashlib.sha256(payload.encode()).hexdigest()[:16].upper()
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


@router.post("/upload", status_code=201)
async def upload_photo(
    file:          UploadFile = File(...),
    project_id:    str        = Form(...),
    enterprise_id: str        = Form(...),
    location:      Optional[str]   = Form(None),
    inspection_id: Optional[str]   = Form(None),
    gps_lat:       Optional[float] = Form(None),
    gps_lng:       Optional[float] = Form(None),
    sb: Client = Depends(get_supabase),
):
    """上传现场照片 · 自动生成 v:// 节点 + Proof"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "只支持图片文件")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, "文件超过 20MB")

    # 获取项目 v:// URI
    proj = sb.table("projects").select("v_uri")\
             .eq("id", project_id).single().execute()
    if not proj.data:
        raise HTTPException(404, "项目不存在")

    proj_uri = proj.data["v_uri"]

    # 上传到 Supabase Storage
    ts           = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    storage_path = f"{enterprise_id}/{project_id}/{ts}_{file.filename}"

    sb.storage.from_("qcspec-photos").upload(
        storage_path, content,
        file_options={"content-type": file.content_type}
    )
    public_url = sb.storage.from_("qcspec-photos").get_public_url(storage_path)

    # 写数据库
    photo_res = sb.table("photos").insert({
        "project_id":    project_id,
        "enterprise_id": enterprise_id,
        "inspection_id": inspection_id,
        "file_name":     file.filename,
        "storage_path":  storage_path,
        "storage_url":   public_url if isinstance(public_url, str) else "",
        "location":      location,
        "gps_lat":       gps_lat,
        "gps_lng":       gps_lng,
        "file_size":     len(content),
        "taken_at":      datetime.utcnow().isoformat(),
    }).execute()

    if not photo_res.data:
        raise HTTPException(500, "照片写入失败")

    photo    = photo_res.data[0]
    photo_id = photo["id"]
    v_uri    = f"{proj_uri}photo/{photo_id}/"
    proof_id = _gen_proof(v_uri, {"file": file.filename, "location": location})

    # 回写 Proof
    sb.table("photos").update({
        "v_uri": v_uri, "proof_id": proof_id,
        "proof_hash": proof_id.replace("GP-PROOF-", "").lower(),
    }).eq("id", photo_id).execute()

    safe_location = (location or "").strip() or "未知桩号"

    # Proof 链
    sb.table("proof_chain").insert({
        "proof_id":      proof_id,
        "proof_hash":    proof_id.replace("GP-PROOF-", "").lower(),
        "enterprise_id": enterprise_id,
        "project_id":    project_id,
        "v_uri":         v_uri,
        "object_type":   "photo",
        "object_id":     photo_id,
        "action":        "upload",
        "summary":       f"照片上传·{safe_location}·{file.filename}",
        "status":        "confirmed",
    }).execute()

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
                "file_name": file.filename,
                "location": location,
                "inspection_id": inspection_id,
                "storage_path": storage_path,
                "storage_url": public_url if isinstance(public_url, str) else "",
                "gps_lat": gps_lat,
                "gps_lng": gps_lng,
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
        "photo_id":    photo_id,
        "v_uri":       v_uri,
        "proof_id":    proof_id,
        "storage_url": public_url,
        "location":    location,
    }


@router.get("/")
async def list_photos(
    project_id:    str,
    inspection_id: Optional[str] = None,
    limit:         int = 50,
    sb: Client = Depends(get_supabase),
):
    q = sb.table("photos").select("*")\
          .eq("project_id", project_id)\
          .order("created_at", desc=True).limit(limit)
    if inspection_id:
        q = q.eq("inspection_id", inspection_id)
    res = q.execute()
    return {"data": res.data, "count": len(res.data)}


@router.delete("/{photo_id}")
async def delete_photo(photo_id: str, sb: Client = Depends(get_supabase)):
    photo = sb.table("photos").select("storage_path,proof_id")\
               .eq("id", photo_id).single().execute()
    if photo.data:
        try:
            sb.storage.from_("qcspec-photos").remove([photo.data["storage_path"]])
        except Exception:
            pass
        try:
            sb.table("proof_chain").delete()\
              .eq("object_type", "photo")\
              .eq("object_id", photo_id).execute()
            if photo.data.get("proof_id"):
                sb.table("proof_chain").delete()\
                  .eq("proof_id", photo.data["proof_id"]).execute()
        except Exception:
            pass
    sb.table("photos").delete().eq("id", photo_id).execute()
    return {"ok": True}

"""
QCSpec · Proof 链路由
services/api/routers/proof.py
"""

from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client, Client
from typing import Optional
import os, hashlib, json

router = APIRouter()

def get_supabase() -> Client:
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


@router.get("/")
async def list_proofs(
    project_id: str,
    v_uri:      Optional[str] = None,
    limit:      int = 50,
    sb: Client  = Depends(get_supabase),
):
    """查询 Proof 链"""
    q = sb.table("proof_chain")\
          .select("proof_id,proof_hash,v_uri,object_type,action,summary,created_at")\
          .eq("project_id", project_id)\
          .order("created_at", desc=True)\
          .limit(limit)
    if v_uri:
        q = q.eq("v_uri", v_uri)
    res = q.execute()
    return {"data": res.data, "count": len(res.data)}


@router.get("/verify/{proof_id}")
async def verify_proof(
    proof_id: str,
    sb: Client = Depends(get_supabase),
):
    """
    验证 Proof 真实性
    返回：valid / proof详情 / 链长度
    """
    res = sb.table("proof_chain").select("*")\
            .eq("proof_id", proof_id).single().execute()

    if not res.data:
        return {"valid": False, "proof": None, "message": "Proof 不存在"}

    proof = res.data

    # 验证哈希一致性
    expected_hash = proof_id.replace("GP-PROOF-", "").lower()
    hash_valid = proof["proof_hash"] == expected_hash

    # 查链长度
    chain_len = sb.table("proof_chain").select("proof_id", count="exact")\
                  .eq("v_uri", proof["v_uri"]).execute()

    return {
        "valid":        hash_valid,
        "proof_id":     proof_id,
        "v_uri":        proof["v_uri"],
        "object_type":  proof["object_type"],
        "action":       proof["action"],
        "summary":      proof["summary"],
        "created_at":   proof["created_at"],
        "chain_length": chain_len.count or 0,
        "message":      "✓ Proof 验证通过" if hash_valid else "✗ 哈希不一致",
    }


@router.get("/node-tree")
async def get_node_tree(
    root_uri: str,
    sb: Client = Depends(get_supabase),
):
    """查询 v:// 节点树"""
    # 查所有以 root_uri 开头的节点
    res = sb.table("v_nodes").select("uri,parent_uri,node_type,peg_count,status")\
            .like("uri", f"{root_uri}%")\
            .order("uri").execute()
    return {"data": res.data, "root": root_uri}


@router.get("/stats/{project_id}")
async def proof_stats(
    project_id: str,
    sb: Client  = Depends(get_supabase),
):
    """Proof 链统计"""
    res = sb.table("proof_chain").select("object_type, action")\
            .eq("project_id", project_id).execute()
    rows = res.data or []

    by_type = {}
    by_action = {}
    for r in rows:
        t = r["object_type"]
        a = r["action"]
        by_type[t]   = by_type.get(t, 0) + 1
        by_action[a] = by_action.get(a, 0) + 1

    return {
        "total":     len(rows),
        "by_type":   by_type,
        "by_action": by_action,
    }

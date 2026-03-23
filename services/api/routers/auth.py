"""
QCSpec · 认证路由
services/api/routers/auth.py

当前：简单 Bearer Token 验证
后期：替换为 Supabase Auth + v:// 主权身份
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from supabase import create_client, Client
from typing import Optional
import os

router  = APIRouter()
security = HTTPBearer()

def get_supabase() -> Client:
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


class LoginRequest(BaseModel):
    email:    str
    password: str

class LoginResponse(BaseModel):
    access_token:  str
    user_id:       str
    name:          str
    dto_role:      str
    enterprise_id: str
    v_uri:         str


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    sb:   Client = Depends(get_supabase),
):
    """
    登录接口
    生产环境使用 Supabase Auth
    当前用简单查询模拟
    """
    # 查用户（生产环境替换为 supabase.auth.sign_in_with_password）
    user_res = sb.table("users").select("*")\
                 .eq("email", body.email)\
                 .eq("is_active", True)\
                 .single().execute()

    if not user_res.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

    user = user_res.data

    # 生产环境：验证密码哈希
    # 当前：直接通过（用于开发调试）
    if os.getenv("DEBUG") != "true":
        raise HTTPException(401, "请配置 Supabase Auth")

    # 生成简单 token（生产替换为 JWT）
    import hashlib, time
    token = hashlib.sha256(
        f"{user['id']}{time.time()}".encode()
    ).hexdigest()

    return LoginResponse(
        access_token  = token,
        user_id       = user["id"],
        name          = user["name"],
        dto_role      = user["dto_role"],
        enterprise_id = user["enterprise_id"],
        v_uri         = user["v_uri"],
    )


@router.get("/me")
async def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    sb: Client   = Depends(get_supabase),
):
    """获取当前用户信息（通过 Bearer Token）"""
    # 生产环境：解码 JWT → 查 Supabase Auth → 返回用户
    # 当前：返回占位数据
    return {
        "message": "后期接入 Supabase Auth",
        "token":   credentials.credentials[:8] + "...",
    }


@router.get("/enterprise/{enterprise_id}")
async def get_enterprise(
    enterprise_id: str,
    sb: Client = Depends(get_supabase),
):
    """获取企业信息"""
    res = sb.table("enterprises").select("*")\
            .eq("id", enterprise_id).single().execute()
    if not res.data:
        raise HTTPException(404, "企业不存在")
    return res.data

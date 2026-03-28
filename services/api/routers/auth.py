"""
QCSpec auth routes
services/api/routers/auth.py
"""

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from supabase import Client

from services.api.auth_service import (
    get_enterprise_flow,
    get_me_flow,
    login_flow,
    logout_flow,
    register_enterprise_flow,
    require_auth_user,
)
from services.api.dependencies import get_supabase_for_auth

router = APIRouter()
security = HTTPBearer()


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterEnterpriseRequest(BaseModel):
    name: str
    adminPhone: str
    password: str
    creditCode: str | None = None
    adminEmail: str | None = None
    adminName: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    user_id: str
    name: str
    dto_role: str
    enterprise_id: str
    v_uri: str


def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    sb: Client = Depends(get_supabase_for_auth),
) -> dict:
    return require_auth_user(token=credentials.credentials, sb=sb)


@router.post("/register-enterprise", status_code=201)
async def register_enterprise(
    body: RegisterEnterpriseRequest,
    sb: Client = Depends(get_supabase_for_auth),
):
    return register_enterprise_flow(body=body, sb=sb)


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    sb: Client = Depends(get_supabase_for_auth),
):
    return login_flow(body=body, sb=sb)


@router.get("/me")
async def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    sb: Client = Depends(get_supabase_for_auth),
):
    return get_me_flow(token=credentials.credentials, sb=sb)


@router.post("/logout")
async def logout_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    sb: Client = Depends(get_supabase_for_auth),
):
    return logout_flow(token=credentials.credentials, sb=sb)


@router.get("/enterprise/{enterprise_id}")
async def get_enterprise(
    enterprise_id: str,
    sb: Client = Depends(get_supabase_for_auth),
):
    return get_enterprise_flow(enterprise_id=enterprise_id, sb=sb)

"""
QCSpec auth routes
services/api/routers/auth.py
"""

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from services.api.dependencies import get_auth_service
from services.api.domain.auth import AuthService

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


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    return await auth_service.require_auth_identity(token=credentials.credentials)


@router.post("/register-enterprise", status_code=201)
async def register_enterprise(
    body: RegisterEnterpriseRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.register_enterprise(body=body)


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.login(body=body)


@router.get("/me")
async def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.get_me(token=credentials.credentials)


@router.post("/logout")
async def logout_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.logout(token=credentials.credentials)


@router.get("/enterprise/{enterprise_id}")
async def get_enterprise(
    enterprise_id: str,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.get_enterprise(enterprise_id=enterprise_id)

"""
QCSpec · 认证路由
services/api/routers/auth.py

当前：简单 Bearer Token 验证
后期：替换为 Supabase Auth + v:// 主权身份
"""

import os
import base64
import hashlib
import hmac
import json
import re
import time
from functools import lru_cache
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from postgrest.exceptions import APIError
from pydantic import BaseModel
from supabase import Client, create_client

router  = APIRouter()
security = HTTPBearer()
_REVOKED_TOKEN_HASHES: dict[str, int] = {}
_ACTIVE_USER_CACHE: dict[str, tuple[int, dict]] = {}
_ACTIVE_USER_CACHE_TTL_SECONDS = int(os.getenv("AUTH_ACTIVE_USER_CACHE_TTL_SECONDS", "90"))


def _ensure_no_proxy_for_supabase() -> None:
    supabase_url = str(os.getenv("SUPABASE_URL") or "").strip()
    if not supabase_url:
        return
    host = urlparse(supabase_url).hostname
    if not host:
        return

    no_proxy_raw = (
        str(os.getenv("NO_PROXY") or "").strip()
        or str(os.getenv("no_proxy") or "").strip()
    )
    entries = {item.strip() for item in no_proxy_raw.split(",") if item.strip()}
    extra = {host, f".{host}", ".supabase.co"}
    merged = ",".join(sorted(entries | extra))
    os.environ["NO_PROXY"] = merged
    os.environ["no_proxy"] = merged


@lru_cache(maxsize=1)
def _supabase_client_cached(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase() -> Client:
    _ensure_no_proxy_for_supabase()
    url = str(os.getenv("SUPABASE_URL") or "").strip()
    key = str(
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    ).strip()
    if not url or not key:
        raise HTTPException(500, "Supabase not configured")
    return _supabase_client_cached(url, key)


class LoginRequest(BaseModel):
    email:    str
    password: str


class RegisterEnterpriseRequest(BaseModel):
    name: str
    adminPhone: str
    password: str
    creditCode: str | None = None
    adminEmail: str | None = None
    adminName: str | None = None


class LoginResponse(BaseModel):
    access_token:  str
    user_id:       str
    name:          str
    dto_role:      str
    enterprise_id: str
    v_uri:         str


def _slugify(value: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "", str(value or "").strip()).lower()
    return slug[:24] or "enterprise"


def _api_error_info(exc: Exception) -> tuple[str, str, str]:
    if isinstance(exc, APIError) and exc.args and isinstance(exc.args[0], dict):
        payload = exc.args[0]
        return (
            str(payload.get("code") or ""),
            str(payload.get("message") or ""),
            str(payload.get("details") or ""),
        )
    return "", "", str(exc)


def _execute(
    request_builder,
    *,
    operation: str = "database request",
    retries: int = 2,
    base_delay_seconds: float = 0.12,
):
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return request_builder.execute()
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt >= retries:
                break
            time.sleep(base_delay_seconds * (2 ** attempt))

    raise HTTPException(
        status_code=503,
        detail=f"{operation} failed: storage temporarily unavailable",
    ) from last_exc


def _prune_active_user_cache(now: int | None = None) -> None:
    ts = int(now or time.time())
    expired = [uid for uid, (exp, _) in _ACTIVE_USER_CACHE.items() if exp <= ts]
    for uid in expired:
        _ACTIVE_USER_CACHE.pop(uid, None)


def _cache_active_user(uid: str, user: dict) -> None:
    _prune_active_user_cache()
    _ACTIVE_USER_CACHE[str(uid)] = (int(time.time()) + _ACTIVE_USER_CACHE_TTL_SECONDS, user)


def _get_cached_active_user(uid: str) -> dict | None:
    _prune_active_user_cache()
    record = _ACTIVE_USER_CACHE.get(str(uid))
    if not record:
        return None
    return record[1]


def _email_exists(sb: Client, email: str) -> bool:
    candidate = str(email or "").strip().lower()
    if not candidate:
        return False
    found = _execute(
        sb.table("users").select("id").eq("email", candidate).limit(1),
        operation="check existing email",
    )
    return bool(found.data)


def _phone_exists(sb: Client, phone: str) -> bool:
    candidate = str(phone or "").strip()
    if not candidate:
        return False
    found = _execute(
        sb.table("users").select("id").eq("phone", candidate).limit(1),
        operation="check existing phone",
    )
    return bool(found.data)


def _allocate_admin_email(sb: Client, admin_phone: str, admin_email: str | None = None) -> str:
    requested = str(admin_email or "").strip().lower()
    if requested:
        if _email_exists(sb, requested):
            raise HTTPException(status_code=409, detail="管理员邮箱已存在，请更换后重试")
        return requested

    local = re.sub(r"[^a-z0-9._+-]+", "", str(admin_phone or "").strip().lower()) or "admin"
    base = f"{local}@qcspec.local"
    if not _email_exists(sb, base):
        return base

    for suffix in range(1, 500):
        candidate = f"{local}+{suffix}@qcspec.local"
        if not _email_exists(sb, candidate):
            return candidate
    raise HTTPException(status_code=500, detail="failed to allocate admin email")


def _token_secret() -> str:
    secret = str(os.getenv("AUTH_TOKEN_SECRET") or "").strip()
    if secret:
        return secret
    fallback = str(
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    ).strip()
    if fallback:
        return fallback
    raise HTTPException(500, "auth secret not configured")


def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64u_decode(raw: str) -> bytes:
    padding = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("utf-8"))


def _mint_token(user_id: str, ttl_seconds: int = 8 * 3600) -> str:
    payload = {
        "uid": str(user_id),
        "iat": int(time.time()),
        "exp": int(time.time()) + int(ttl_seconds),
    }
    payload_raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    payload_b64 = _b64u_encode(payload_raw)
    signature = hmac.new(_token_secret().encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"qca1.{payload_b64}.{signature}"


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _prune_revoked(now: int | None = None) -> None:
    ts = int(now or time.time())
    expired = [fp for fp, exp in _REVOKED_TOKEN_HASHES.items() if exp <= ts]
    for fp in expired:
        _REVOKED_TOKEN_HASHES.pop(fp, None)


def _revoke_token(token: str, exp: int) -> None:
    _prune_revoked()
    _REVOKED_TOKEN_HASHES[_token_fingerprint(token)] = int(exp)


def _is_revoked(token: str) -> bool:
    _prune_revoked()
    return _token_fingerprint(token) in _REVOKED_TOKEN_HASHES


def _parse_token(token: str) -> dict:
    if _is_revoked(token):
        raise HTTPException(status_code=401, detail="token revoked")

    parts = str(token or "").split(".")
    if len(parts) != 3 or parts[0] != "qca1":
        raise HTTPException(status_code=401, detail="invalid token")

    _, payload_b64, signature = parts
    expected = hmac.new(_token_secret().encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="invalid token signature")

    try:
        payload = json.loads(_b64u_decode(payload_b64).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid token payload") from exc

    uid = str(payload.get("uid") or "").strip()
    exp = int(payload.get("exp") or 0)
    now = int(time.time())
    if not uid:
        raise HTTPException(status_code=401, detail="invalid token subject")
    if exp <= now:
        raise HTTPException(status_code=401, detail="token expired")

    return payload


def _load_active_user(sb: Client, uid: str) -> dict | None:
    res = _execute(
        sb.table("users")
        .select("id,name,email,phone,title,dto_role,enterprise_id,v_uri,is_active")
        .eq("id", uid)
        .eq("is_active", True)
        .limit(1),
        operation="load active user",
    )
    rows = res.data or []
    return rows[0] if rows else None


def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    sb: Client = Depends(get_supabase),
) -> dict:
    payload = _parse_token(credentials.credentials)
    uid = str(payload.get("uid"))
    cached_user = _get_cached_active_user(uid)
    try:
        user = _load_active_user(sb, uid)
    except HTTPException as exc:
        if exc.status_code == 503 and cached_user:
            return cached_user
        raise
    if not user:
        _ACTIVE_USER_CACHE.pop(uid, None)
        raise HTTPException(status_code=401, detail="user not found or inactive")
    _cache_active_user(uid, user)
    return user


@router.post("/register-enterprise", status_code=201)
async def register_enterprise(
    body: RegisterEnterpriseRequest,
    sb: Client = Depends(get_supabase),
):
    name = str(body.name or "").strip()
    admin_phone = str(body.adminPhone or "").strip()
    password = str(body.password or "")
    if not name or not admin_phone or not password:
        raise HTTPException(status_code=400, detail="name, adminPhone and password are required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="password must be at least 6 chars")
    if _phone_exists(sb, admin_phone):
        raise HTTPException(status_code=409, detail="该手机号已存在管理员账号，请直接登录")

    base_slug = _slugify(name)
    v_uri: str | None = None
    for i in range(0, 100):
        slug = base_slug if i == 0 else f"{base_slug}{i}"
        candidate_uri = f"v://cn/{slug}/"
        exists = _execute(
            sb.table("enterprises").select("id").eq("v_uri", candidate_uri).limit(1),
            operation="check enterprise uri",
        )
        if not exists.data:
            v_uri = candidate_uri
            break
    if not v_uri:
        raise HTTPException(status_code=500, detail="failed to allocate enterprise uri")

    try:
        ent_res = sb.table("enterprises").insert(
            {
                "v_uri": v_uri,
                "name": name,
                "short_name": name[:16],
                "credit_code": str(body.creditCode or "").strip() or None,
                "plan": "enterprise",
                "proof_quota": 500,
                "proof_used": 0,
            }
        )
        ent_res = _execute(ent_res, operation="create enterprise")
    except APIError as exc:
        code, message, details = _api_error_info(exc)
        if code == "23505":
            if "enterprises_v_uri_key" in message:
                raise HTTPException(status_code=409, detail="企业标识冲突，请重试注册") from exc
            if "enterprises_credit_code_key" in message:
                raise HTTPException(status_code=409, detail="统一社会信用代码已存在") from exc
        raise HTTPException(
            status_code=500,
            detail=f"failed to create enterprise: {message or details or 'unknown error'}",
        ) from exc

    if not ent_res.data:
        raise HTTPException(status_code=500, detail="failed to create enterprise")
    enterprise = ent_res.data[0]
    enterprise_id = enterprise["id"]

    try:
        _execute(
            sb.table("enterprise_configs").insert({"enterprise_id": enterprise_id}),
            operation="create enterprise config",
        )
    except Exception:
        pass

    account_email = _allocate_admin_email(sb, admin_phone=admin_phone, admin_email=body.adminEmail)
    admin_name = str(body.adminName or "").strip() or "管理员"
    user_uri = f"{v_uri}executor/{_slugify(admin_name)}/"
    password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

    try:
        user_res = sb.table("users").insert(
            {
                "enterprise_id": enterprise_id,
                "v_uri": user_uri,
                "name": admin_name,
                "phone": admin_phone,
                "email": account_email,
                "password_hash": password_hash,
                "dto_role": "OWNER",
                "title": "超级管理员",
                "is_active": True,
            }
        )
        user_res = _execute(user_res, operation="create admin user")
    except APIError as exc:
        code, message, details = _api_error_info(exc)
        try:
            _execute(
                sb.table("enterprises").delete().eq("id", enterprise_id),
                operation="rollback enterprise",
            )
        except Exception:
            # Best effort rollback for non-transactional flow.
            pass

        if code == "23505":
            if "users_email_key" in message:
                raise HTTPException(status_code=409, detail="管理员邮箱已存在，请更换后重试") from exc
            if "users_v_uri_key" in message:
                raise HTTPException(status_code=409, detail="管理员标识冲突，请重试注册") from exc
        raise HTTPException(
            status_code=500,
            detail=f"failed to create admin user: {message or details or 'unknown error'}",
        ) from exc

    if not user_res.data:
        raise HTTPException(status_code=500, detail="failed to create admin user")

    return {
        "ok": True,
        "enterprise_id": enterprise_id,
        "enterprise_name": enterprise.get("name"),
        "admin_user_id": user_res.data[0].get("id"),
        "account": admin_phone,
    }


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
    account = str(body.email or "").strip()
    # 查用户（支持邮箱、手机号、邮箱前缀登录）
    user_res = (
        sb.table("users")
        .select("*")
        .eq("email", account)
        .eq("is_active", True)
        .limit(1)
    )
    user_res = _execute(user_res, operation="login query by email")
    user = user_res.data[0] if user_res.data else None
    if not user:
        user_res = (
            sb.table("users")
            .select("*")
            .eq("phone", account)
            .eq("is_active", True)
            .limit(1)
        )
        user_res = _execute(user_res, operation="login query by phone")
        user = user_res.data[0] if user_res.data else None
    if not user and "@" not in account:
        user_res = (
            sb.table("users")
            .select("*")
            .ilike("email", f"{account}@%")
            .eq("is_active", True)
            .limit(1)
        )
        user_res = _execute(user_res, operation="login query by alias")
        user = user_res.data[0] if user_res.data else None

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

    provided_hash = hashlib.sha256(str(body.password or "").encode("utf-8")).hexdigest()
    stored_hash = str(user.get("password_hash") or "").strip()
    if stored_hash:
        if not hmac.compare_digest(stored_hash, provided_hash):
            raise HTTPException(status_code=401, detail="邮箱或密码错误")
    elif os.getenv("DEBUG") != "true":
        raise HTTPException(401, "请配置 Supabase Auth")

    # 生成签名 token（当前用于开发联调）
    token = _mint_token(user["id"])

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
    payload = _parse_token(credentials.credentials)
    uid = str(payload.get("uid"))
    user = _load_active_user(sb, uid)
    if not user:
        raise HTTPException(status_code=401, detail="user not found or inactive")

    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "title": user.get("title"),
        "dto_role": user.get("dto_role"),
        "enterprise_id": user.get("enterprise_id"),
        "v_uri": user.get("v_uri"),
        "token_exp": payload.get("exp"),
    }


@router.post("/logout")
async def logout_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    payload = _parse_token(credentials.credentials)
    _revoke_token(credentials.credentials, int(payload.get("exp") or int(time.time())))
    return {"ok": True}


@router.get("/enterprise/{enterprise_id}")
async def get_enterprise(
    enterprise_id: str,
    sb: Client = Depends(get_supabase),
):
    """获取企业信息"""
    res = sb.table("enterprises").select("*")\
            .eq("id", enterprise_id).single()
    res = _execute(res, operation="load enterprise")
    if not res.data:
        raise HTTPException(404, "企业不存在")
    return res.data

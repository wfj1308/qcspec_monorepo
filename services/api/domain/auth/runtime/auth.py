"""
Auth domain service functions shared by auth router.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import re
import time
from typing import Any
from urllib.parse import urlparse

import bcrypt
import httpx
from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from supabase import Client

_REVOKED_TOKEN_HASHES: dict[str, int] = {}
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_AUTH_FAIL_CLOSED_REVOKE = str(os.getenv("AUTH_FAIL_CLOSED_REVOKE", "true")).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_AUTH_ALLOW_MISSING_REVOKE_TABLE = str(
    os.getenv("AUTH_ALLOW_MISSING_REVOKE_TABLE", "true")
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def ensure_no_proxy_for_supabase() -> None:
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


def api_error_info(exc: Exception) -> tuple[str, str, str]:
    if isinstance(exc, APIError) and exc.args and isinstance(exc.args[0], dict):
        payload = exc.args[0]
        return (
            str(payload.get("code") or ""),
            str(payload.get("message") or ""),
            str(payload.get("details") or ""),
        )
    return "", "", str(exc)


def execute(
    request_builder: Any,
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
        status_code=502,
        detail=f"{operation} failed: storage temporarily unavailable",
    ) from last_exc


def _email_exists(sb: Client, email: str) -> bool:
    candidate = str(email or "").strip().lower()
    if not candidate:
        return False
    found = execute(
        sb.table("users").select("id").eq("email", candidate).limit(1),
        operation="check existing email",
    )
    return bool(found.data)


def _phone_exists(sb: Client, phone: str) -> bool:
    candidate = str(phone or "").strip()
    if not candidate:
        return False
    found = execute(
        sb.table("users").select("id").eq("phone", candidate).limit(1),
        operation="check existing phone",
    )
    return bool(found.data)


def _allocate_admin_email(sb: Client, admin_phone: str, admin_email: str | None = None) -> str:
    requested = str(admin_email or "").strip().lower()
    if requested:
        if _email_exists(sb, requested):
            raise HTTPException(status_code=409, detail="admin email already exists")
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


def _slugify(value: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "", str(value or "").strip()).lower()
    return slug[:24] or "enterprise"


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
    secret = str(os.getenv("AUTH_REVOKE_FP_SECRET") or "").strip() or _token_secret()
    return hmac.new(secret.encode("utf-8"), str(token or "").encode("utf-8"), hashlib.sha256).hexdigest()


def _legacy_token_fingerprint(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _token_fingerprint_candidates(token: str) -> list[str]:
    current = _token_fingerprint(token)
    legacy = _legacy_token_fingerprint(token)
    if legacy == current:
        return [current]
    return [current, legacy]


def _is_bcrypt_hash(value: str) -> bool:
    text = str(value or "").strip()
    return text.startswith("$2a$") or text.startswith("$2b$") or text.startswith("$2y$")


def _is_legacy_sha256_hash(value: str) -> bool:
    text = str(value or "").strip().lower()
    return bool(_SHA256_HEX_RE.fullmatch(text))


def _hash_password(raw_password: str) -> str:
    password = str(raw_password or "")
    rounds = int(str(os.getenv("AUTH_BCRYPT_ROUNDS") or "12"))
    rounds = max(10, min(rounds, 15))
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def _verify_password(raw_password: str, stored_hash: str) -> bool:
    password = str(raw_password or "")
    hashed = str(stored_hash or "").strip()
    if not hashed:
        return False
    if _is_bcrypt_hash(hashed):
        try:
            return bool(bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8")))
        except ValueError:
            return False
    legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return bool(hmac.compare_digest(hashed, legacy_hash))


def _prune_revoked(now: int | None = None) -> None:
    ts = int(now or time.time())
    expired = [fp for fp, exp in _REVOKED_TOKEN_HASHES.items() if exp <= ts]
    for fp in expired:
        _REVOKED_TOKEN_HASHES.pop(fp, None)


def _to_utc_iso(ts_seconds: int) -> str:
    return datetime.fromtimestamp(int(ts_seconds), tz=timezone.utc).isoformat()


def _parse_utc_iso(raw: str) -> int | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except Exception:
        return None


def _is_missing_revoke_table_error(exc: Exception) -> bool:
    code, message, details = api_error_info(exc)
    merged = " ".join(
        [
            str(code or ""),
            str(message or ""),
            str(details or ""),
            str(exc or ""),
        ]
    ).lower()
    if "auth_revoked_tokens" not in merged:
        return False
    return True


def _revoke_token(token: str, exp: int, sb: Client | None = None) -> None:
    exp_i = int(exp)
    _prune_revoked()
    token_fp = _token_fingerprint(token)
    _REVOKED_TOKEN_HASHES[token_fp] = exp_i
    if sb is None:
        return
    try:
        execute(
            sb.table("auth_revoked_tokens").upsert(
                {
                    "token_fp": token_fp,
                    "expires_at": _to_utc_iso(exp_i),
                },
                on_conflict="token_fp",
            ),
            operation="persist revoked token",
            retries=0,
        )
    except Exception as exc:
        if _AUTH_ALLOW_MISSING_REVOKE_TABLE and _is_missing_revoke_table_error(exc):
            return
        if _AUTH_FAIL_CLOSED_REVOKE:
            raise HTTPException(status_code=502, detail="revoke store unavailable") from exc


def _is_revoked(token: str, sb: Client | None = None) -> bool:
    token_fps = _token_fingerprint_candidates(token)
    _prune_revoked()
    for token_fp in token_fps:
        if token_fp in _REVOKED_TOKEN_HASHES:
            return True
    if sb is None:
        return False
    try:
        res = execute(
            sb.table("auth_revoked_tokens")
            .select("token_fp,expires_at")
            .in_("token_fp", token_fps)
            .limit(2),
            operation="check revoked token",
            retries=0,
        )
    except Exception as exc:
        if _AUTH_ALLOW_MISSING_REVOKE_TABLE and _is_missing_revoke_table_error(exc):
            return False
        if _AUTH_FAIL_CLOSED_REVOKE:
            raise HTTPException(status_code=502, detail="revoke check unavailable") from exc
        return False
    rows = [row for row in (res.data or []) if isinstance(row, dict)]
    if not rows:
        return False
    row = rows[0]
    token_fp = str(row.get("token_fp") or "")
    exp_ts = _parse_utc_iso(str(row.get("expires_at") or ""))
    now_ts = int(time.time())
    if exp_ts is None or exp_ts <= now_ts:
        for candidate in token_fps:
            _REVOKED_TOKEN_HASHES.pop(candidate, None)
        try:
            execute(
                sb.table("auth_revoked_tokens").delete().in_("token_fp", token_fps),
                operation="cleanup expired revoked token",
                retries=0,
            )
        except Exception:
            pass
        return False
    _REVOKED_TOKEN_HASHES[token_fp] = int(exp_ts)
    return True


def _parse_token(token: str, sb: Client | None = None) -> dict[str, Any]:
    if _is_revoked(token, sb=sb):
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


def _load_active_user(sb: Client, uid: str) -> dict[str, Any] | None:
    res = execute(
        sb.table("users")
        .select("id,name,email,phone,title,dto_role,enterprise_id,v_uri,is_active")
        .eq("id", uid)
        .eq("is_active", True)
        .limit(1),
        operation="load active user",
    )
    rows = res.data or []
    return rows[0] if rows else None


def require_auth_user(*, token: str, sb: Client) -> dict[str, Any]:
    payload = _parse_token(token, sb=sb)
    uid = str(payload.get("uid"))
    user = _load_active_user(sb, uid)

    if not user:
        raise HTTPException(status_code=401, detail="user not found or inactive")
    return user


def register_enterprise_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    name = str(body.name or "").strip()
    admin_phone = str(body.adminPhone or "").strip()
    password = str(body.password or "")
    if not name or not admin_phone or not password:
        raise HTTPException(status_code=400, detail="name, adminPhone and password are required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="password must be at least 6 chars")
    if _phone_exists(sb, admin_phone):
        raise HTTPException(status_code=409, detail="admin phone already exists")

    base_slug = _slugify(name)
    v_uri: str | None = None
    for i in range(0, 100):
        slug = base_slug if i == 0 else f"{base_slug}{i}"
        candidate_uri = f"v://cn/{slug}/"
        exists = execute(
            sb.table("enterprises").select("id").eq("v_uri", candidate_uri).limit(1),
            operation="check enterprise uri",
        )
        if not exists.data:
            v_uri = candidate_uri
            break
    if not v_uri:
        raise HTTPException(status_code=500, detail="failed to allocate enterprise uri")

    try:
        ent_res = execute(
            sb.table("enterprises").insert(
                {
                    "v_uri": v_uri,
                    "name": name,
                    "short_name": name[:16],
                    "credit_code": str(body.creditCode or "").strip() or None,
                    "plan": "enterprise",
                    "proof_quota": 500,
                    "proof_used": 0,
                }
            ),
            operation="create enterprise",
        )
    except APIError as exc:
        code, message, details = api_error_info(exc)
        if code == "23505":
            if "enterprises_v_uri_key" in message:
                raise HTTPException(status_code=409, detail="enterprise uri conflict") from exc
            if "enterprises_credit_code_key" in message:
                raise HTTPException(status_code=409, detail="credit code already exists") from exc
        raise HTTPException(
            status_code=500,
            detail=f"failed to create enterprise: {message or details or 'unknown error'}",
        ) from exc

    if not ent_res.data:
        raise HTTPException(status_code=500, detail="failed to create enterprise")

    enterprise = ent_res.data[0]
    enterprise_id = enterprise["id"]

    try:
        execute(
            sb.table("enterprise_configs").insert({"enterprise_id": enterprise_id}),
            operation="create enterprise config",
        )
    except Exception:
        pass

    account_email = _allocate_admin_email(sb, admin_phone=admin_phone, admin_email=body.adminEmail)
    admin_name = str(body.adminName or "").strip() or "Admin"
    user_uri = f"{v_uri}executor/{_slugify(admin_name)}/"
    password_hash = _hash_password(password)

    try:
        user_res = execute(
            sb.table("users").insert(
                {
                    "enterprise_id": enterprise_id,
                    "v_uri": user_uri,
                    "name": admin_name,
                    "phone": admin_phone,
                    "email": account_email,
                    "password_hash": password_hash,
                    "dto_role": "OWNER",
                    "title": "Super Admin",
                    "is_active": True,
                }
            ),
            operation="create admin user",
        )
    except APIError as exc:
        code, message, details = api_error_info(exc)
        try:
            execute(
                sb.table("enterprises").delete().eq("id", enterprise_id),
                operation="rollback enterprise",
            )
        except Exception:
            pass

        if code == "23505":
            if "users_email_key" in message:
                raise HTTPException(status_code=409, detail="admin email already exists") from exc
            if "users_v_uri_key" in message:
                raise HTTPException(status_code=409, detail="admin uri conflict") from exc
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


def login_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    account = str(body.email or "").strip()

    user_res = execute(
        sb.table("users")
        .select("*")
        .eq("email", account)
        .eq("is_active", True)
        .limit(1),
        operation="login query by email",
    )
    user = user_res.data[0] if user_res.data else None

    if not user:
        user_res = execute(
            sb.table("users")
            .select("*")
            .eq("phone", account)
            .eq("is_active", True)
            .limit(1),
            operation="login query by phone",
        )
        user = user_res.data[0] if user_res.data else None

    if not user and "@" not in account:
        user_res = execute(
            sb.table("users")
            .select("*")
            .ilike("email", f"{account}@%")
            .eq("is_active", True)
            .limit(1),
            operation="login query by alias",
        )
        user = user_res.data[0] if user_res.data else None

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid email/phone or password",
        )

    stored_hash = str(user.get("password_hash") or "").strip()
    if stored_hash:
        if not _verify_password(body.password, stored_hash):
            raise HTTPException(status_code=401, detail="invalid email/phone or password")
        if _is_legacy_sha256_hash(stored_hash):
            try:
                execute(
                    sb.table("users")
                    .update({"password_hash": _hash_password(body.password)})
                    .eq("id", user["id"]),
                    operation="upgrade password hash",
                    retries=0,
                )
            except Exception:
                pass
    elif os.getenv("DEBUG") != "true":
        raise HTTPException(401, "missing password hash configuration")

    token = _mint_token(user["id"])
    return {
        "access_token": token,
        "user_id": user["id"],
        "name": user.get("name") or "",
        "dto_role": user.get("dto_role") or "",
        "enterprise_id": user.get("enterprise_id") or "",
        "v_uri": user.get("v_uri") or "",
    }


def get_me_flow(*, token: str, sb: Client) -> dict[str, Any]:
    payload = _parse_token(token, sb=sb)
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


def logout_flow(*, token: str, sb: Client) -> dict[str, Any]:
    payload = _parse_token(token, sb=sb)
    _revoke_token(token, int(payload.get("exp") or int(time.time())), sb=sb)
    return {"ok": True}


def get_enterprise_flow(*, enterprise_id: str, sb: Client) -> dict[str, Any]:
    res = execute(
        sb.table("enterprises").select("*").eq("id", enterprise_id).single(),
        operation="load enterprise",
    )
    if not res.data:
        raise HTTPException(404, "enterprise not found")
    return res.data

"""Account-aware bearer sessions with legacy bootstrap access."""

from __future__ import annotations

import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Header, HTTPException, status
from jose import JWTError, jwt

ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 480
DEVICE_SESSION_SECONDS = 30 * 24 * 3600
VALID_ROLES = frozenset({"admin", "demo", "guest", "member", "viewer"})


def _read_passwords() -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    admin_password = os.getenv("ADMIN_PASSWORD")
    demo_password = os.getenv("DEMO_PASSWORD")
    guest_password = os.getenv("GUEST_PASSWORD")
    master_password = os.getenv("STOCKSCOPE_PASSWORD", admin_password)
    return admin_password, demo_password, guest_password, master_password


def _jwt_secret() -> str:
    """Require a dedicated signing key; never derive one from login credentials."""
    secret = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET")
    if not secret or len(secret.strip()) < 32:
        raise ValueError("SECRET_KEY or JWT_SECRET must contain at least 32 characters")
    if secret == "stockscope-insecure-dev-secret-change-me" or secret in _read_passwords():
        raise ValueError("The signing key must be dedicated and different from login passwords")
    return secret


def get_access_token_expire_minutes() -> int:
    minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)))
    if minutes <= 0:
        raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
    return minutes


def validate_auth_config() -> None:
    """Fail closed before serving requests with missing or unsafe configuration."""
    admin_password, demo_password, guest_password, _ = _read_passwords()
    for name, value in (("ADMIN_PASSWORD", admin_password), ("DEMO_PASSWORD", demo_password), ("GUEST_PASSWORD", guest_password)):
        if not value or not value.strip():
            raise ValueError(f"{name} environment variable must be set")
    if len({admin_password, demo_password, guest_password}) != 3:
        raise ValueError("Admin, demo, and guest passwords must be different")
    _jwt_secret()
    get_access_token_expire_minutes()


def get_user_role(password: str) -> Optional[str]:
    admin_password, demo_password, guest_password, master_password = _read_passwords()
    for configured, role in ((admin_password, "admin"), (demo_password, "demo"), (guest_password, "guest"), (master_password, "admin")):
        if configured and hmac.compare_digest(password.encode("utf-8"), configured.encode("utf-8")):
            return role
    return None


async def authenticate_user(password: str) -> tuple[bool, Optional[str]]:
    role = get_user_role(password)
    return role is not None, role


def create_access_token(subject: str, role: str, expires_minutes: Optional[float] = None, session_version: Optional[int] = None) -> str:
    minutes = expires_minutes if expires_minutes is not None else get_access_token_expire_minutes()
    return _signed_token(subject, role, timedelta(minutes=minutes), session_version, "access")


def create_device_token(user) -> str:
    return _signed_token("user:" + user.id, user.role, timedelta(seconds=DEVICE_SESSION_SECONDS),
                         user.session_version, "device")


def _signed_token(subject, role, lifetime, session_version, purpose):
    if not subject.strip() or role not in VALID_ROLES:
        raise ValueError("A nonempty subject and a known role are required")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "exp": now + lifetime,
        "iat": now,
        "type": purpose,
    }
    if session_version is not None:
        payload["version"] = session_version
    return jwt.encode(payload, _jwt_secret(), algorithm=ALGORITHM)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def _decode_access_token(token: str, *, purpose="access") -> dict:
    secret = _jwt_secret()
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
    except (JWTError, ValueError, TypeError, OverflowError) as exc:
        raise _unauthorized("Invalid or expired token") from exc

    issued_at, expires_at = payload.get("iat"), payload.get("exp")
    if (
        payload.get("type") != purpose
        or not isinstance(payload.get("role"), str)
        or payload["role"] not in VALID_ROLES
        or not isinstance(payload.get("sub"), str)
        or not payload["sub"].strip()
        or type(issued_at) not in (int, float)
        or type(expires_at) not in (int, float)
        or not issued_at < expires_at
        or issued_at > datetime.now(timezone.utc).timestamp() + 60
    ):
        raise _unauthorized("Invalid token payload")
    return payload


def _active_account(payload):
    from backend.services.accounts import account_repository
    from backend.db.models import WorkspaceUser
    with account_repository().session_factory() as session:
        user = session.get(WorkspaceUser, payload["sub"][5:])
        if not user or not user.active or user.session_version != payload.get("version"):
            raise _unauthorized("Your access has ended. Sign in again or contact the owner.")
        return user


def device_account(token):
    payload = _decode_access_token(token, purpose="device")
    if not payload["sub"].startswith("user:"):
        raise _unauthorized("Invalid device session")
    return _active_account(payload), payload["exp"]


def authenticate_token(authorization):
    if not authorization:
        raise _unauthorized("Sign in to obtain an Authorization Bearer token")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise _unauthorized("Invalid Authorization header format")
    payload = _decode_access_token(parts[1].strip())
    if payload["sub"].startswith("user:"):
        return _active_account(payload)
    from backend.services.research import repository
    if repository() is None:
        if os.getenv("ALLOW_LEGACY_FILE_AUTH", "false").lower() != "true":
            raise _unauthorized("Private accounts require the workspace database.")
    else:
        # Shared sessions cease to work once the owner creates their account.
        from backend.services.accounts import has_users
        if payload["role"] != "admin" or has_users():
            raise _unauthorized("Use your invited account to sign in.")
    return payload["role"]


async def verify_password_with_role(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    import asyncio
    from backend.core.resources import yahoo_principal
    user = await asyncio.to_thread(authenticate_token, authorization)
    # Bind on the ASGI request task, before it dispatches sync endpoints or workers.
    yahoo_principal.set('legacy:' + user if isinstance(user, str) else user.id)
    return user if isinstance(user, str) else user.role


def current_account(authorization: Optional[str] = Header(None, alias="Authorization")):
    user = authenticate_token(authorization)
    if isinstance(user, str):
        raise HTTPException(403, "Set up your individual owner account first.")
    return user

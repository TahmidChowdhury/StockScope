"""Regression coverage for bearer sessions and fail-closed signing configuration."""
import asyncio
import inspect
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from jose import jwt

from backend.core.auth import authenticate_user, create_access_token, validate_auth_config, verify_password_with_role

TEST_SECRET = "test-signing-secret-that-is-at-least-32-characters"


@pytest.fixture(autouse=True)
def auth_env(monkeypatch):
    for key, value in {"ADMIN_PASSWORD": "admin-pass", "DEMO_PASSWORD": "demo-pass", "GUEST_PASSWORD": "guest-pass", "SECRET_KEY": TEST_SECRET}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("STOCKSCOPE_PASSWORD", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)


def verify(token):
    return asyncio.run(verify_password_with_role(authorization=f"Bearer {token}"))


@pytest.mark.parametrize("role", ["admin", "demo", "guest"])
def test_valid_signed_session_preserves_role(role):
    token = create_access_token(subject="test-user", role=role, expires_minutes=5)
    assert verify(token) == role


def test_login_authenticates_known_password_only():
    assert asyncio.run(authenticate_user("demo-pass")) == (True, "demo")
    assert asyncio.run(authenticate_user("wrong")) == (False, None)


@pytest.mark.parametrize("header", [None, "Basic anything", "Bearer ", "Bearer invalid-token"])
def test_rejects_missing_or_invalid_credentials(header):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(verify_password_with_role(authorization=header))
    assert exc.value.status_code == 401
    assert exc.value.headers["WWW-Authenticate"] == "Bearer"


def test_query_password_auth_is_no_longer_exposed():
    assert "password" not in inspect.signature(verify_password_with_role).parameters


def test_expired_token_rejected():
    with pytest.raises(HTTPException) as exc:
        verify(create_access_token("test-user", "admin", expires_minutes=-1))
    assert exc.value.status_code == 401


def test_other_signing_key_rejected():
    now = int(datetime.now(timezone.utc).timestamp())
    token = jwt.encode({"sub": "attacker", "role": "admin", "type": "access", "iat": now, "exp": now + 300}, "stockscope-insecure-dev-secret-change-me", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        verify(token)
    assert exc.value.status_code == 401


@pytest.mark.parametrize("claim", ["sub", "iat", "exp", "type", "role"])
def test_required_claims_cannot_be_omitted(claim):
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {"sub": "test-user", "role": "admin", "type": "access", "iat": now, "exp": now + 300}
    del payload[claim]
    with pytest.raises(HTTPException) as exc:
        verify(jwt.encode(payload, TEST_SECRET, algorithm="HS256"))
    assert exc.value.status_code == 401


@pytest.mark.parametrize("changes", [{"role": []}, {"role": "superadmin"}, {"type": "refresh"}, {"sub": " "}, {"iat": 9999999999}, {"iat": "123"}])
def test_invalid_claims_rejected(changes):
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {"sub": "test-user", "role": "admin", "type": "access", "iat": now, "exp": now + 300, **changes}
    with pytest.raises(HTTPException) as exc:
        verify(jwt.encode(payload, TEST_SECRET, algorithm="HS256"))
    assert exc.value.status_code == 401


@pytest.mark.parametrize("secret", [None, "short", " " * 40, "stockscope-insecure-dev-secret-change-me"])
def test_startup_rejects_missing_or_unsafe_secret(monkeypatch, secret):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    if secret is not None:
        monkeypatch.setenv("SECRET_KEY", secret)
    with pytest.raises(ValueError):
        validate_auth_config()


def test_login_password_is_never_a_signing_key_fallback(monkeypatch):
    monkeypatch.delenv("SECRET_KEY")
    monkeypatch.setenv("STOCKSCOPE_PASSWORD", "a-long-master-password-with-more-than-32-characters")
    with pytest.raises(ValueError):
        validate_auth_config()


def test_signing_key_must_differ_from_login_passwords(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", TEST_SECRET)
    with pytest.raises(ValueError):
        validate_auth_config()


def test_jwt_secret_alias_and_dynamic_expiry(monkeypatch):
    monkeypatch.delenv("SECRET_KEY")
    monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10")
    validate_auth_config()
    payload = jwt.decode(create_access_token("test-user", "guest"), TEST_SECRET, algorithms=["HS256"])
    assert payload["exp"] - payload["iat"] == 600

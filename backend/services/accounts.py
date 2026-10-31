"""Local account management. No public signup or paid email service is required."""
from __future__ import annotations

from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import hashlib
import hmac
import re
import secrets
from collections import defaultdict, deque
from datetime import timedelta
from threading import RLock
from time import monotonic

from fastapi import HTTPException
from sqlalchemy import func, select, update

from backend.db.models import WorkspaceUser, WorkspaceInvite, ResourceState, utcnow
from backend.db.repository import timestamp
from backend.services.research import repository

_auth_lock = RLock()
_attempts = defaultdict(deque)


def account_repository():
    from backend.services import research
    repo = research.repository()
    if repo is None:
        raise HTTPException(503, "A migrated database is required for private accounts.")
    return repo


def throttle(key):
    """Bound hashing work and guessing; one API process is the supported deployment."""
    with _auth_lock:
        now = monotonic()
        for old in list(_attempts):
            while _attempts[old] and _attempts[old][0] <= now - 900:
                _attempts[old].popleft()
            if not _attempts[old]:
                del _attempts[old]
        for bucket, limit in (("global", 100), (key, 10)):
            if len(_attempts[bucket]) >= limit:
                raise HTTPException(429, "Too many sign-in attempts. Try again in 15 minutes.", headers={"Retry-After": "900"})
        _attempts["global"].append(now)
        _attempts[key].append(now)


def email_key(value):
    value = value.strip().lower()
    if len(value) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise HTTPException(422, "Enter a valid email address.")
    return value


def hash_password(password, salt=None):
    if not 12 <= len(password) <= 128:
        raise HTTPException(422, "Use a password between 12 and 128 characters.")
    salt = salt or secrets.token_hex(16)
    # OWASP scrypt parameters; serialize work to bound memory on a small host.
    with _auth_lock:
        result = Scrypt(salt=bytes.fromhex(salt), length=64, n=2**17, r=8, p=1).derive(password.encode())
    return f"scrypt-v1${salt}${result.hex()}"


def valid_password(password, encoded):
    if not 12 <= len(password) <= 128:
        return False
    try:
        version, salt, _ = encoded.split("$")
        return version == "scrypt-v1" and hmac.compare_digest(hash_password(password, salt), encoded)
    except (ValueError, TypeError):
        return False


def public_user(user):
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role,
            "active": user.active, "created_at": user.created_at}


def lock_accounts(session):
    # Seeded by migration; serializes bootstrap, invite acceptance and admin changes.
    if session.scalar(select(ResourceState).where(ResourceState.key == "accounts").with_for_update()) is None:
        raise HTTPException(503, "Account schema is not initialized.")


def has_users():
    with account_repository().session_factory() as session:
        return bool(session.scalar(select(WorkspaceUser.id).limit(1)))


def bootstrap(email, name, password, owner_password):
    from backend.core.auth import get_user_role
    if get_user_role(owner_password) != "admin":
        raise HTTPException(401, "Owner setup credentials are invalid.")
    encoded = hash_password(password)
    with _auth_lock, account_repository().session_factory.begin() as session:
        lock_accounts(session)
        if session.scalar(select(WorkspaceUser.id).limit(1)):
            raise HTTPException(409, "Owner setup has already been completed.")
        user = WorkspaceUser(email=email_key(email), name=name.strip(), password_hash=encoded, role="admin")
        session.add(user)
        session.flush()
        return user


def login(email, password):
    with account_repository().session_factory() as session:
        user = session.scalar(select(WorkspaceUser).where(WorkspaceUser.email == email_key(email)))
        # Equal-cost hashing for unknown users, without revealing membership.
        encoded = user.password_hash if user else "scrypt-v1$" + "00" * 16 + "$" + "00" * 64
        accepted = valid_password(password, encoded)
        if not user or not user.active or not accepted:
            raise HTTPException(401, "Email or password is incorrect, or access is unavailable.")
        return user


def issue_invite(actor, email, role, *, reset=False):
    email = email_key(email)
    token = secrets.token_urlsafe(32)
    with _auth_lock, account_repository().session_factory.begin() as session:
        lock_accounts(session)
        current_actor = session.get(WorkspaceUser, actor.id)
        if not current_actor or not current_actor.active or current_actor.role != 'admin' or current_actor.session_version != actor.session_version:
            raise HTTPException(403, "Your administrator access has changed.")
        existing = session.scalar(select(WorkspaceUser).where(WorkspaceUser.email == email))
        if reset and (not existing or not existing.active):
            raise HTTPException(409, "Restore the account's access before creating a reset link.")
        if reset:
            role = existing.role
        count = session.scalar(select(func.count()).select_from(WorkspaceUser))
        pending = session.scalar(select(func.count()).select_from(WorkspaceInvite).where(
            WorkspaceInvite.revoked.is_(False), WorkspaceInvite.used_at.is_(None), WorkspaceInvite.expires_at > utcnow(), WorkspaceInvite.email != email))
        if not reset and count + pending >= 25:
            raise HTTPException(409, "This workspace is limited to 25 accounts and pending invitations.")
        if existing and not reset:
            raise HTTPException(409, "That account already exists. Manage its access below.")
        session.execute(update(WorkspaceInvite).where(WorkspaceInvite.email == email).values(revoked=True))
        invite = WorkspaceInvite(email=email, role=role, token_hash=hashlib.sha256(token.encode()).hexdigest(),
                                 created_by=actor.id, expires_at=utcnow() + timedelta(days=3))
        session.add(invite)
        session.flush()
        return {"id": invite.id, "email": email, "role": role, "token": token, "expires_at": invite.expires_at}


def accept_invite(token, email, name, password):
    encoded = hash_password(password)
    with _auth_lock, account_repository().session_factory.begin() as session:
        lock_accounts(session)
        invite = session.scalar(select(WorkspaceInvite).where(WorkspaceInvite.token_hash == hashlib.sha256(token.encode()).hexdigest()).with_for_update())
        if not invite or invite.revoked or invite.used_at or timestamp(invite.expires_at) <= utcnow() or invite.email != email_key(email):
            raise HTTPException(400, "Invitation is invalid, expired, or addressed to a different email.")
        user = session.scalar(select(WorkspaceUser).where(WorkspaceUser.email == invite.email))
        if user:
            if not user.active:
                raise HTTPException(400, "This account's access has been suspended.")
            user.password_hash = encoded
            user.session_version += 1
        else:
            user = WorkspaceUser(email=invite.email, name=name.strip(), password_hash=encoded, role=invite.role)
            session.add(user)
        invite.used_at = utcnow()
        session.flush()
        return user

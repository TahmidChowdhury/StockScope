"""Private identities and owner-scoped lists; all access is enforced server-side."""
from typing import Literal
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, update

from backend.core.auth import (DEVICE_SESSION_SECONDS, create_access_token, create_device_token, current_account,
                               device_account, get_access_token_expire_minutes)
from backend.db.models import PersonalList, PersonalListItem, WorkspaceUser, WorkspaceInvite, utcnow
from backend.db.repository import symbol_key
from backend.services import accounts

router = APIRouter()
Role = Literal['admin', 'member', 'viewer']


class Credentials(BaseModel):
    remember_device: bool = False
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Registration(Credentials):
    name: str = Field(min_length=1, max_length=80, pattern=r'.*\S.*')
    token: str = Field(default='', max_length=128)
    owner_password: str = Field(default='', max_length=256)


class Invitation(BaseModel):
    email: str = Field(max_length=254)
    role: Role = 'member'


class AccessChange(BaseModel):
    active: bool
    role: Role


class ListName(BaseModel):
    name: str = Field(min_length=1, max_length=80, pattern=r'.*\S.*')


class ItemInput(BaseModel):
    symbol: str = Field(min_length=1, max_length=10, pattern=r'^[a-zA-Z][a-zA-Z0-9.\-]{0,9}$')
    pinned: bool = False


def admin(user=Depends(current_account)):
    if user.role != 'admin':
        raise HTTPException(403, 'Owner access is required.')
    return user


def response(user, remember_device=False, device_expiry=None):
    seconds = get_access_token_expire_minutes() * 60
    if device_expiry is not None:
        seconds = min(seconds, int(device_expiry - time.time()))
        if seconds <= 0:
            raise HTTPException(401, "Device session expired.")
    result = {"success": True, "message": "Signed in", "role": user.role,
            "user": accounts.public_user(user), "token_type": "bearer",
            "expires_in_seconds": seconds,
            "access_token": create_access_token('user:' + user.id, user.role, expires_minutes=seconds / 60,
                                                session_version=user.session_version)}
    if remember_device:
        result.update(device_token=create_device_token(user), device_max_age=DEVICE_SESSION_SECONDS)
    return result


def limit(request):
    # Do not trust caller-controlled forwarding headers.
    accounts.throttle('auth:' + (request.client.host if request.client else 'unknown'))


@router.get('/auth/config')
def config():
    return {"invite_only": True, "setup_required": not accounts.has_users()}


@router.post('/auth/sign-in')
def sign_in(body: Credentials, request: Request):
    limit(request)
    return response(accounts.login(body.email, body.password), body.remember_device)


@router.post('/auth/setup', status_code=201)
def setup(body: Registration, request: Request):
    limit(request)
    return response(accounts.bootstrap(body.email, body.name, body.password, body.owner_password), body.remember_device)


@router.post('/auth/accept-invite', status_code=201)
def accept(body: Registration, request: Request):
    limit(request)
    return response(accounts.accept_invite(body.token, body.email, body.name, body.password), body.remember_device)


class DeviceCredential(BaseModel):
    token: str = Field(min_length=1, max_length=4096)


@router.post('/auth/resume')
def resume(body: DeviceCredential):
    user, expiry = device_account(body.token)
    return response(user, device_expiry=expiry)


@router.post('/auth/sign-out')
def sign_out(user=Depends(current_account)):
    with accounts.account_repository().session_factory.begin() as session:
        session.execute(update(WorkspaceUser).where(WorkspaceUser.id == user.id).values(session_version=WorkspaceUser.session_version + 1))
    return {"signed_out": True}


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


@router.post('/auth/password')
def change_password(body: PasswordChange, request: Request, user=Depends(current_account)):
    limit(request)
    if not accounts.valid_password(body.current_password, user.password_hash):
        raise HTTPException(400, 'Current password is incorrect.')
    encoded = accounts.hash_password(body.new_password)
    with accounts.account_repository().session_factory.begin() as session:
        session.execute(update(WorkspaceUser).where(WorkspaceUser.id == user.id).values(password_hash=encoded, session_version=WorkspaceUser.session_version + 1))
    return {"changed": True, "sign_in_required": True}


@router.get('/account/yahoo-usage')
def my_yahoo_usage(user=Depends(current_account)):
    from backend.core.resources import personal_yahoo_usage
    return personal_yahoo_usage(user.id)


@router.get('/resources')
def resources(user=Depends(admin)):
    from backend.core.resources import usage_summary
    return {"providers": usage_summary(), "research_cooldown_hours": 6, "automatic_research": False}


@router.get('/access')
def access(user=Depends(admin)):
    with accounts.account_repository().session_factory() as session:
        return {"users": [accounts.public_user(row) for row in session.scalars(select(WorkspaceUser).order_by(WorkspaceUser.created_at))],
                "invites": [{"id": row.id, "email": row.email, "role": row.role, "expires_at": row.expires_at}
                            for row in session.scalars(select(WorkspaceInvite).where(WorkspaceInvite.used_at.is_(None), WorkspaceInvite.revoked.is_(False), WorkspaceInvite.expires_at > utcnow()))]}


@router.post('/access/invites', status_code=201)
def invite(body: Invitation, user=Depends(admin)):
    return accounts.issue_invite(user, body.email, body.role)


@router.post('/access/users/{user_id}/reset')
def reset_password(user_id: str, user=Depends(admin)):
    with accounts.account_repository().session_factory() as session:
        target = session.get(WorkspaceUser, user_id)
        if not target:
            raise HTTPException(404, 'Account not found.')
        return accounts.issue_invite(user, target.email, target.role, reset=True)


@router.delete('/access/invites/{invite_id}')
def revoke_invite(invite_id: str, user=Depends(admin)):
    with accounts.account_repository().session_factory.begin() as session:
        session.execute(update(WorkspaceInvite).where(WorkspaceInvite.id == invite_id).values(revoked=True))
    return {"revoked": True}


@router.put('/access/users/{user_id}')
def update_access(user_id: str, body: AccessChange, user=Depends(admin)):
    if user_id == user.id:
        raise HTTPException(409, 'You cannot change your own access here.')
    with accounts._auth_lock, accounts.account_repository().session_factory.begin() as session:
        accounts.lock_accounts(session)
        actor = session.get(WorkspaceUser, user.id)
        if not actor or not actor.active or actor.role != 'admin' or actor.session_version != user.session_version:
            raise HTTPException(403, 'Your administrator access has changed.')
        target = session.get(WorkspaceUser, user_id)
        if not target:
            raise HTTPException(404, 'Account not found.')
        target.active, target.role = body.active, body.role
        target.session_version += 1
        if not target.active or target.role != 'admin':
            session.execute(update(WorkspaceInvite).where(WorkspaceInvite.created_by == target.id, WorkspaceInvite.used_at.is_(None)).values(revoked=True))
        return accounts.public_user(target)


def owned(session, list_id, user):
    row = session.scalar(select(PersonalList).where(PersonalList.id == list_id, PersonalList.owner_id == user.id).with_for_update())
    if row is None:
        raise HTTPException(404, 'List not found.')
    return row


@router.get('/lists')
def lists(user=Depends(current_account)):
    with accounts.account_repository().session_factory() as session:
        rows = session.scalars(select(PersonalList).where(PersonalList.owner_id == user.id).order_by(PersonalList.created_at)).all()
        items = session.scalars(select(PersonalListItem).join(PersonalList).where(PersonalList.owner_id == user.id).order_by(PersonalListItem.added_at.desc())).all()
        return [{"id": row.id, "name": row.name, "items": [{"symbol": item.symbol, "pinned": item.pinned} for item in items if item.list_id == row.id]} for row in rows]


@router.post('/lists', status_code=201)
def create_list(body: ListName, user=Depends(current_account)):
    with accounts.account_repository().session_factory.begin() as session:
        session.scalar(select(WorkspaceUser).where(WorkspaceUser.id == user.id).with_for_update())
        if session.scalar(select(func.count()).select_from(PersonalList).where(PersonalList.owner_id == user.id)) >= 20:
            raise HTTPException(409, 'You can keep up to 20 personal lists.')
        name = body.name.strip()
        if session.scalar(select(PersonalList.id).where(PersonalList.owner_id == user.id, PersonalList.name == name)):
            raise HTTPException(409, 'You already have a list with that name.')
        row = PersonalList(owner_id=user.id, name=name)
        session.add(row)
        session.flush()
        return {"id": row.id, "name": row.name, "items": []}


@router.put('/lists/{list_id}')
def rename_list(list_id: str, body: ListName, user=Depends(current_account)):
    with accounts.account_repository().session_factory.begin() as session:
        session.scalar(select(WorkspaceUser).where(WorkspaceUser.id == user.id).with_for_update())
        row = owned(session, list_id, user)
        if session.scalar(select(PersonalList.id).where(PersonalList.owner_id == user.id, PersonalList.name == body.name.strip(), PersonalList.id != list_id)):
            raise HTTPException(409, 'You already have a list with that name.')
        row.name = body.name.strip()
        return {"id": row.id, "name": row.name}


@router.delete('/lists/{list_id}')
def delete_list(list_id: str, user=Depends(current_account)):
    with accounts.account_repository().session_factory.begin() as session:
        row = owned(session, list_id, user)
        session.execute(delete(PersonalListItem).where(PersonalListItem.list_id == row.id))
        session.delete(row)
    return {"removed": True}


class BatchItems(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=50)


@router.put('/lists/{list_id}/items/batch')
def save_items(list_id: str, body: BatchItems, user=Depends(current_account)):
    try:
        symbols = list(dict.fromkeys(symbol_key(value) for value in body.symbols))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with accounts.account_repository().session_factory.begin() as session:
        owned(session, list_id, user)
        existing = set(session.scalars(select(PersonalListItem.symbol).where(PersonalListItem.list_id == list_id)))
        if len(existing | set(symbols)) > 250:
            raise HTTPException(409, 'Each list can contain up to 250 companies.')
        for symbol in symbols:
            if symbol not in existing:
                session.add(PersonalListItem(list_id=list_id, symbol=symbol, pinned=False))
    return {"saved": len(symbols)}


@router.put('/lists/{list_id}/items')
def save_item(list_id: str, body: ItemInput, user=Depends(current_account)):
    with accounts.account_repository().session_factory.begin() as session:
        owned(session, list_id, user)
        symbol = symbol_key(body.symbol)
        item = session.get(PersonalListItem, (list_id, symbol))
        if not item:
            if session.scalar(select(func.count()).select_from(PersonalListItem).where(PersonalListItem.list_id == list_id)) >= 250:
                raise HTTPException(409, 'Each list can contain up to 250 companies.')
            item = PersonalListItem(list_id=list_id, symbol=symbol)
            session.add(item)
        item.pinned = body.pinned
    return {"saved": True}


@router.delete('/lists/{list_id}/items/{symbol}')
def remove_item(list_id: str, symbol: str, user=Depends(current_account)):
    with accounts.account_repository().session_factory.begin() as session:
        owned(session, list_id, user)
        session.execute(delete(PersonalListItem).where(PersonalListItem.list_id == list_id, PersonalListItem.symbol == symbol.upper()))
    return {"removed": True}

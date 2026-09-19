"""Authentication service: login, refresh-rotation, logout, password flows."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from app.core.datetime import as_utc, utcnow
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.permissions import Role
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.user import RefreshToken, User, UserStatus
from app.services.audit_service import log_action


def _find_user(db: Session, identifier: str) -> Optional[User]:
    ident = identifier.strip()
    return (
        db.query(User)
        .filter((User.email == ident.lower()) | (User.college_id == ident))
        .first()
    )


def _hash_token(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authenticate(db: Session, identifier: str, password: str, ip: str | None = None) -> User:
    user = _find_user(db, identifier)
    if not user or not verify_password(password, user.password_hash):
        # Constant-ish failure message to avoid account enumeration.
        raise UnauthorizedError("Invalid credentials. Please check your email/College ID and password.")
    if user.status != UserStatus.ACTIVE:
        raise ForbiddenError("Your account has been suspended. Please contact the administrator.")

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    log_action(
        db,
        user_id=user.id,
        user_name=user.name,
        role=str(user.role),
        action="user.login",
        resource="auth",
        ip_address=ip,
    )
    return user


def issue_tokens(db: Session, user: User, ip: str | None = None, user_agent: str | None = None) -> dict:
    access, access_exp = create_access_token(user.id, user.role)
    refresh, jti, refresh_exp = create_refresh_token(user.id)

    record = RefreshToken(
        user_id=user.id,
        jti=jti,
        token_hash=_hash_token(refresh),
        expires_at=refresh_exp,
        ip=ip,
        user_agent=(user_agent or "")[:255],
    )
    db.add(record)
    db.commit()

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "expires_at": access_exp.isoformat(),
        "user": user.to_public_dict(),
    }


def refresh_session(db: Session, refresh_token: str, ip: str | None = None) -> dict:
    """Rotate: validate the presented refresh token, revoke it, issue a new pair."""
    try:
        payload = decode_refresh_token(refresh_token)
    except Exception:
        raise UnauthorizedError("Invalid or expired refresh token. Please log in again.")

    jti = payload.get("jti")
    record = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not record or record.revoked:
        raise UnauthorizedError("This session has been revoked. Please log in again.")
    if record.token_hash != _hash_token(refresh_token):
        # Token reuse after rotation -> revoke the whole family (single active session).
        record.revoked = True
        db.commit()
        raise UnauthorizedError("Session reuse detected. Please log in again.")
    if as_utc(record.expires_at) < utcnow():
        record.revoked = True
        db.commit()
        raise UnauthorizedError("Your session has expired. Please log in again.")

    user = record.user
    if not user or user.status != UserStatus.ACTIVE:
        raise ForbiddenError("Your account is not active.")

    # Rotate: invalidate the presented token, mint a fresh pair.
    record.revoked = True
    db.commit()
    return issue_tokens(db, user, ip=ip)


def logout(db: Session, refresh_token: str) -> None:
    try:
        payload = decode_refresh_token(refresh_token)
    except Exception:
        return  # idempotent logout
    record = db.query(RefreshToken).filter(RefreshToken.jti == payload.get("jti")).first()
    if record and not record.revoked:
        record.revoked = True
        db.commit()
        log_action(
            db,
            user_id=record.user_id,
            user_name=None,
            role=None,
            action="user.logout",
            resource="auth",
            ip_address=None,
        )


def revoke_all_sessions(db: Session, user_id: int) -> int:
    rows = db.query(RefreshToken).filter(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False)).all()
    for r in rows:
        r.revoked = True
    db.commit()
    return len(rows)


def change_password(db: Session, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        raise UnauthorizedError("Your current password is incorrect.")
    if current == new:
        raise BadRequestError("The new password must be different from the current one.")
    user.password_hash = hash_password(new)
    user.must_change_password = False
    db.commit()
    revoke_all_sessions(db, user.id)
    log_action(
        db,
        user_id=user.id,
        user_name=user.name,
        role=str(user.role),
        action="user.password_change",
        resource="user",
        resource_id=user.id,
    )


def create_password_reset_token(db: Session, identifier: str) -> Optional[tuple[User, str]]:
    """Issue a single-use reset token. The token is returned to the caller
    (router emails it / displays it in demo mode)."""
    user = _find_user(db, identifier)
    if not user:
        return None
    token = secrets.token_urlsafe(32)
    user.password_hash = user.password_hash  # no-op keeps hash
    # Store the reset token as a dedicated refresh-family entry.
    rt = RefreshToken(
        user_id=user.id,
        jti=f"reset-{token}",
        token_hash=_hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(rt)
    db.commit()
    return user, token


def reset_password(db: Session, token: str, new_password: str) -> User:
    record = (
        db.query(RefreshToken)
        .filter(RefreshToken.jti.like("reset-%"), RefreshToken.token_hash == _hash_token(token))
        .first()
    )
    if not record or record.revoked:
        raise UnauthorizedError("This reset link is invalid or has already been used.")
    if as_utc(record.expires_at) < utcnow():
        raise UnauthorizedError("This reset link has expired. Please request a new one.")
    user = record.user
    if not user:
        raise NotFoundError("User not found.")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    record.revoked = True
    db.commit()
    revoke_all_sessions(db, user.id)
    log_action(
        db,
        user_id=user.id,
        user_name=user.name,
        role=str(user.role),
        action="user.password_reset",
        resource="user",
        resource_id=user.id,
    )
    return user


def create_user_account(
    db: Session,
    *,
    name: str,
    email: str,
    college_id: str,
    role: Role | str,
    password: Optional[str] = None,
    phone: Optional[str] = None,
    status: UserStatus = UserStatus.ACTIVE,
) -> tuple[User, str]:
    """Create a user with a generated (or provided) password. Returns (user, plaintext)."""
    if db.query(User).filter((User.email == email.lower()) | (User.college_id == college_id)).first():
        raise ConflictError("A user with this email or College ID already exists.")

    plaintext = password or secrets.token_urlsafe(10)
    user = User(
        college_id=college_id,
        name=name,
        email=email.lower(),
        phone=phone,
        password_hash=hash_password(plaintext),
        role=str(role),
        status=str(status),
        must_change_password=password is None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, plaintext

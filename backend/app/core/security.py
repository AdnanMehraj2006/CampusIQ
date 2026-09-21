"""Password hashing and JWT token utilities.

Access tokens are short-lived and stateless. Refresh tokens are rotating and
revocable: each issued refresh token is stored (hashed) in the database so the
server can invalidate sessions on logout or compromise.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt

from app.config import settings
from app.core.permissions import Role

# ---------------------------------------------------------------------------
# Password hashing (bcrypt, cost 12)
# ---------------------------------------------------------------------------

_BCRYPT_COST = 12


def hash_password(password: str) -> str:
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    salt = bcrypt.gensalt(rounds=_BCRYPT_COST)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """True when the hash was made with a weaker cost than the current policy.

    bcrypt encodes the cost in the hash prefix (``$2b$12$...``), so we parse it
    rather than depending on a library helper that bcrypt 5 no longer exposes.
    """
    try:
        parts = hashed_password.split("$")
        if len(parts) < 3:
            return True
        return int(parts[2]) < _BCRYPT_COST
    except (ValueError, TypeError, IndexError):
        return True


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

ALGORITHM = settings.jwt_algorithm


def _create_token(
    subject: str,
    secret: str,
    expires_delta: timedelta,
    token_type: str,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> tuple[str, str, datetime]:
    """Return (token, jti, expiry_utc)."""
    now = datetime.now(timezone.utc)
    jti = _generate_jti()
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "type": token_type,
        "jti": jti,
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, secret, algorithm=ALGORITHM)
    return token, jti, now + expires_delta


def _generate_jti() -> str:
    import secrets

    return secrets.token_hex(16)


def create_access_token(
    user_id: str | int,
    role: Role | str,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> tuple[str, datetime]:
    token, _jti, exp = _create_token(
        subject=str(user_id),
        secret=settings._jwt_secret,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        token_type="access",
        extra_claims={"role": str(role), **(extra_claims or {})},
    )
    return token, exp


def create_refresh_token(user_id: str | int) -> tuple[str, str, datetime]:
    token, jti, exp = _create_token(
        subject=str(user_id),
        secret=settings._jwt_refresh_secret,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        token_type="refresh",
    )
    return token, jti, exp


def decode_token(token: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
    """Decode + validate a token. Raises ``jwt.InvalidTokenError`` variants."""
    secret = (
        settings._jwt_refresh_secret if expected_type == "refresh" else settings._jwt_secret
    )
    payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Expected {expected_type} token")
    return payload


def decode_access_token(token: str) -> Dict[str, Any]:
    return decode_token(token, expected_type="access")


def decode_refresh_token(token: str) -> Dict[str, Any]:
    return decode_token(token, expected_type="refresh")

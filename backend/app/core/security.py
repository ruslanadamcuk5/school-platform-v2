"""Password hashing, JWT access tokens and opaque refresh tokens."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


class TokenError(ValueError):
    """Raised when an access token is invalid or expired."""


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("BCrypt supports passwords up to 72 bytes")
    return pwd_context.hash(password)


def _verify_legacy_pbkdf2(password: str, password_hash: str) -> bool:
    """Verify the PBKDF2-HMAC-SHA256 format used by the old Flask app.

    Imported accounts keep their original hashes. On the first successful
    login the hash is transparently upgraded to bcrypt by ``needs_rehash``.
    """
    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$")
        if algorithm != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password or not password_hash:
        return False
    if password_hash.startswith("pbkdf2$"):
        return _verify_legacy_pbkdf2(password, password_hash)
    try:
        return pwd_context.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


def needs_rehash(password_hash: str | None) -> bool:
    """Return True for legacy or outdated hashes that should be upgraded."""
    if not password_hash:
        return True
    if password_hash.startswith("pbkdf2$"):
        return True
    try:
        return pwd_context.needs_update(password_hash)
    except (ValueError, TypeError):
        return True


def _read_key(raw_path: str) -> str:
    path = settings.resolve_path(raw_path)
    if not path.exists():
        raise RuntimeError(f"JWT key not found: {path}")
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _private_key() -> str:
    if settings.jwt_algorithm.upper().startswith("HS"):
        return settings.secret_key
    return _read_key(settings.jwt_private_key_path)


@lru_cache(maxsize=1)
def _public_key() -> str:
    if settings.jwt_algorithm.upper().startswith("HS"):
        return settings.secret_key
    return _read_key(settings.jwt_public_key_path)


def create_access_token(
    *,
    user_id: uuid.UUID,
    role: str,
    school_id: uuid.UUID | None,
    ttl_seconds: int | None = None,
    extra: dict | None = None,
) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        seconds=ttl_seconds or settings.access_token_ttl_seconds
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "school_id": str(school_id) if school_id else None,
        "type": "access",
        "jti": uuid.uuid4().hex,
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, _private_key(), algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            _public_key(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except JWTError as exc:
        raise TokenError("Invalid or expired access token") from exc
    if payload.get("type") != "access" or not payload.get("sub"):
        raise TokenError("Invalid access token payload")
    return payload


def new_refresh_token() -> tuple[str, str]:
    """Return ``(raw_token, sha256_hash)``. Only the hash is stored."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def refresh_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        seconds=settings.refresh_token_ttl_seconds
    )


def key_fingerprint() -> str:
    """Short non-secret fingerprint for health/diagnostics."""
    key = _public_key().encode("utf-8")
    return hashlib.sha256(key).hexdigest()[:12]


def private_key_exists() -> bool:
    if settings.jwt_algorithm.upper().startswith("HS"):
        return True
    return Path(settings.resolve_path(settings.jwt_private_key_path)).exists()

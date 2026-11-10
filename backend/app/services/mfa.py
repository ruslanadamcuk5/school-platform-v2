"""TOTP multi-factor authentication helpers.

TOTP secrets are encrypted with Fernet before they reach PostgreSQL.  The
Fernet key comes from ``MFA_ENCRYPTION_KEY``; when it is absent, a key is
derived from ``SECRET_KEY`` so local development keeps working.  Production
must configure a dedicated key and keep it in the secret store.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.iam import MfaRecoveryCode, RefreshToken, User
from app.services.audit import add_audit_event

MFA_PURPOSE_VERIFY = "verify"
MFA_PURPOSE_ENROLL = "enroll"
RECOVERY_CODE_COUNT = 10
TOTP_PERIOD_SECONDS = 30


class MfaError(ValueError):
    """Base MFA validation error."""


class MfaNotConfiguredError(MfaError):
    """MFA is not enabled or has no stored secret."""


class MfaLockedError(MfaError):
    """Too many failed attempts; the account is temporarily locked."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fernet() -> Fernet:
    configured = (settings.mfa_encryption_key or "").strip()
    if configured:
        try:
            return Fernet(configured.encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                "MFA_ENCRYPTION_KEY must be a valid Fernet key"
            ) from exc
    derived = base64.urlsafe_b64encode(
        hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    )
    return Fernet(derived)


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("ascii")).decode("ascii")


def decrypt_secret(token: str | None) -> str:
    if not token:
        raise MfaNotConfiguredError("MFA secret is not configured")
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("ascii")
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
        raise MfaError("MFA secret cannot be decrypted") from exc


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def build_otpauth_uri(secret: str, login: str) -> str:
    label = quote(f"{settings.mfa_issuer}:{login}", safe=":@")
    query = urlencode(
        {
            "secret": secret,
            "issuer": settings.mfa_issuer,
            "algorithm": "SHA1",
            "digits": 6,
            "period": TOTP_PERIOD_SECONDS,
        }
    )
    return f"otpauth://totp/{label}?{query}"


def _hotp(key: bytes, counter: int) -> str:
    digest = hmac.new(
        key,
        struct.pack(">Q", counter),
        hashlib.sha1,
    ).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{value % 1_000_000:06d}"


def totp_code(secret: str, *, at_time: float | None = None) -> str:
    """Generate the current TOTP code (used by tests and diagnostics)."""
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    counter = int(
        (at_time if at_time is not None else time.time()) // TOTP_PERIOD_SECONDS
    )
    return _hotp(key, counter)


def verify_totp(
    secret: str,
    code: str,
    *,
    at_time: float | None = None,
    window: int = 1,
) -> int | None:
    """Return the matched counter, or ``None`` for an invalid code."""
    normalized = code.strip().replace(" ", "")
    if len(normalized) != 6 or not normalized.isdigit():
        return None
    try:
        padded = secret + "=" * ((8 - len(secret) % 8) % 8)
        key = base64.b32decode(padded, casefold=True)
    except (ValueError, TypeError):
        return None
    counter = int((at_time if at_time is not None else time.time()) // TOTP_PERIOD_SECONDS)
    for offset in range(-window, window + 1):
        candidate = counter + offset
        if hmac.compare_digest(_hotp(key, candidate), normalized):
            return candidate
    return None


def normalize_recovery_code(code: str) -> str:
    return code.strip().replace("-", "").replace(" ", "").lower()


def hash_recovery_code(code: str) -> str:
    return hashlib.sha256(normalize_recovery_code(code).encode("utf-8")).hexdigest()


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    codes: list[str] = []
    while len(codes) < count:
        raw = secrets.token_hex(8)
        codes.append("-".join(raw[index : index + 4] for index in range(0, 16, 4)))
    return codes


def _check_lock(user: User) -> None:
    if user.mfa_locked_until is not None:
        if user.mfa_locked_until > _now():
            raise MfaLockedError(
                "Too many MFA attempts; try again after the lockout expires"
            )
        user.mfa_locked_until = None
        user.mfa_failed_attempts = 0


def _reset_failures(user: User) -> None:
    user.mfa_failed_attempts = 0
    user.mfa_locked_until = None


def _register_failure(user: User) -> None:
    attempts = (user.mfa_failed_attempts or 0) + 1
    user.mfa_failed_attempts = attempts
    if attempts >= settings.mfa_max_failed_attempts:
        user.mfa_locked_until = _now() + timedelta(
            minutes=settings.mfa_lockout_minutes
        )


async def start_enrollment(
    session: AsyncSession,
    *,
    user: User,
) -> tuple[str, str]:
    """Create a pending TOTP secret and return ``(secret, otpauth_uri)``."""
    if user.mfa_enabled:
        raise MfaError("MFA is already enabled")
    _check_lock(user)
    secret = generate_totp_secret()
    user.mfa_pending_secret_encrypted = encrypt_secret(secret)
    add_audit_event(
        session,
        action="mfa_enrollment_started",
        entity_type="user",
        entity_id=user.id,
        school_id=user.school_id,
        user_id=user.id,
    )
    return secret, build_otpauth_uri(secret, user.login)


async def complete_enrollment(
    session: AsyncSession,
    *,
    user: User,
    code: str,
) -> list[str]:
    """Verify the first TOTP code, enable MFA and return recovery codes."""
    if user.mfa_enabled:
        raise MfaError("MFA is already enabled")
    _check_lock(user)
    secret = decrypt_secret(user.mfa_pending_secret_encrypted)
    counter = verify_totp(secret, code)
    if counter is None:
        _register_failure(user)
        add_audit_event(
            session,
            action="mfa_enrollment_failed",
            entity_type="user",
            entity_id=user.id,
            school_id=user.school_id,
            user_id=user.id,
        )
        raise MfaError("Invalid MFA code")

    user.mfa_secret_encrypted = user.mfa_pending_secret_encrypted
    user.mfa_pending_secret_encrypted = None
    user.mfa_enabled = True
    user.mfa_enrolled_at = _now()
    user.mfa_last_used_counter = counter
    _reset_failures(user)
    recovery_codes = generate_recovery_codes()
    for recovery_code in recovery_codes:
        session.add(
            MfaRecoveryCode(
                user_id=user.id,
                code_hash=hash_recovery_code(recovery_code),
            )
        )
    add_audit_event(
        session,
        action="mfa_enabled",
        entity_type="user",
        entity_id=user.id,
        school_id=user.school_id,
        user_id=user.id,
    )
    return recovery_codes


async def _consume_recovery_code(
    session: AsyncSession,
    *,
    user: User,
    code: str,
) -> bool:
    normalized = normalize_recovery_code(code)
    if len(normalized) != 16:
        return False
    code_hash = hash_recovery_code(normalized)
    record = (
        await session.execute(
            select(MfaRecoveryCode).where(
                MfaRecoveryCode.user_id == user.id,
                MfaRecoveryCode.code_hash == code_hash,
                MfaRecoveryCode.used_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        return False
    record.used_at = _now()
    return True


async def verify_login_code(
    session: AsyncSession,
    *,
    user: User,
    code: str,
) -> str:
    """Verify TOTP or a recovery code and return the method used."""
    if not user.mfa_enabled:
        raise MfaNotConfiguredError("MFA is not enabled")
    _check_lock(user)
    secret = decrypt_secret(user.mfa_secret_encrypted)
    counter = verify_totp(secret, code)
    if counter is not None and (
        user.mfa_last_used_counter is None
        or counter > user.mfa_last_used_counter
    ):
        user.mfa_last_used_counter = counter
        _reset_failures(user)
        add_audit_event(
            session,
            action="mfa_verified",
            entity_type="user",
            entity_id=user.id,
            school_id=user.school_id,
            user_id=user.id,
            details={"method": "totp"},
        )
        return "totp"

    if await _consume_recovery_code(session, user=user, code=code):
        _reset_failures(user)
        add_audit_event(
            session,
            action="mfa_verified",
            entity_type="user",
            entity_id=user.id,
            school_id=user.school_id,
            user_id=user.id,
            details={"method": "recovery_code"},
        )
        return "recovery_code"

    _register_failure(user)
    add_audit_event(
        session,
        action="mfa_failed",
        entity_type="user",
        entity_id=user.id,
        school_id=user.school_id,
        user_id=user.id,
    )
    raise MfaError("Invalid MFA code")


async def recovery_codes_remaining(
    session: AsyncSession,
    *,
    user_id,
) -> int:
    return int(
        (
            await session.execute(
                select(func.count())
                .select_from(MfaRecoveryCode)
                .where(
                    MfaRecoveryCode.user_id == user_id,
                    MfaRecoveryCode.used_at.is_(None),
                )
            )
        ).scalar_one()
    )


@dataclass(frozen=True)
class MfaResetResult:
    """Summary of an emergency MFA reset; never contains secrets."""

    login: str
    was_enabled: bool
    recovery_codes_deleted: int
    refresh_tokens_revoked: int
    actor: str


async def reset_mfa(
    session: AsyncSession,
    *,
    user: User,
    reason: str,
    actor: str = "cli",
) -> MfaResetResult:
    """Reset MFA, revoke refresh sessions and delete recovery codes.

    The caller must commit the session.  Access tokens already issued remain
    valid until their short TTL expires, so this is an emergency procedure.
    """
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise MfaError("Reason is required")
    if len(normalized_reason) > 500:
        raise MfaError("Reason is too long")

    recovery_codes_deleted = int(
        (
            await session.execute(
                select(func.count())
                .select_from(MfaRecoveryCode)
                .where(MfaRecoveryCode.user_id == user.id)
            )
        ).scalar_one()
    )
    refresh_tokens_revoked = int(
        (
            await session.execute(
                select(func.count())
                .select_from(RefreshToken)
                .where(
                    RefreshToken.user_id == user.id,
                    RefreshToken.revoked_at.is_(None),
                )
            )
        ).scalar_one()
    )

    now = _now()
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
        .execution_options(synchronize_session=False)
    )
    await session.execute(
        delete(MfaRecoveryCode)
        .where(MfaRecoveryCode.user_id == user.id)
        .execution_options(synchronize_session=False)
    )

    was_enabled = bool(user.mfa_enabled)
    user.mfa_enabled = False
    user.mfa_secret_encrypted = None
    user.mfa_pending_secret_encrypted = None
    user.mfa_enrolled_at = None
    user.mfa_last_used_counter = None
    user.mfa_failed_attempts = 0
    user.mfa_locked_until = None

    add_audit_event(
        session,
        action="mfa_reset",
        entity_type="user",
        entity_id=user.id,
        school_id=user.school_id,
        user_id=None,
        details={
            "source": actor,
            "target_login": user.login,
            "target_role": user.role,
            "reason": normalized_reason,
            "was_enabled": was_enabled,
            "recovery_codes_deleted": recovery_codes_deleted,
            "refresh_tokens_revoked": refresh_tokens_revoked,
        },
    )
    return MfaResetResult(
        login=user.login,
        was_enabled=was_enabled,
        recovery_codes_deleted=recovery_codes_deleted,
        refresh_tokens_revoked=refresh_tokens_revoked,
        actor=actor,
    )

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    password = "PilotPass123!"
    stored = hash_password(password)
    assert stored != password
    assert verify_password(password, stored)
    assert not verify_password("wrong-password", stored)


def test_password_too_long_is_rejected() -> None:
    with pytest.raises(ValueError):
        hash_password("x" * 73)


def test_refresh_token_is_opaque_and_stable() -> None:
    raw, hashed = new_refresh_token()
    assert raw != hashed
    assert len(hashed) == 64
    assert hash_refresh_token(raw) == hashed


def test_access_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    school_id = uuid.uuid4()
    token, expires_at = create_access_token(
        user_id=user_id, role="teacher", school_id=school_id
    )
    assert expires_at > datetime.now(timezone.utc)

    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "teacher"
    assert payload["school_id"] == str(school_id)
    assert payload["type"] == "access"


def test_tampered_token_is_rejected() -> None:
    token, _ = create_access_token(
        user_id=uuid.uuid4(), role="student", school_id=None
    )
    with pytest.raises(TokenError):
        decode_access_token(token + "tampered")

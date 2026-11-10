"""MFA/TOTP service, challenge tokens and login API."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import auth as auth_api
from app.core.security import (
    TokenError,
    create_mfa_token,
    decode_access_token,
    decode_mfa_token,
    hash_refresh_token,
)
from app.db.session import get_session
from app.main import app
from app.models.iam import MfaRecoveryCode, RefreshToken, User
from app.services.auth import AuthError, rotate_refresh_token
from app.services.mfa import (
    MFA_PURPOSE_ENROLL,
    MFA_PURPOSE_VERIFY,
    MfaError,
    complete_enrollment,
    decrypt_secret,
    encrypt_secret,
    generate_recovery_codes,
    generate_totp_secret,
    hash_recovery_code,
    start_enrollment,
    totp_code,
    verify_login_code,
    verify_totp,
)


class FakeResult:
    def __init__(self, value=None, rows=None) -> None:
        self.value = value
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, user: User | None = None, scalar_value=None) -> None:
        self.user = user
        self.scalar_value = scalar_value
        self.added: list[object] = []
        self.commits = 0

    async def get(self, model, key, **_kwargs):
        if model is User and self.user is not None and self.user.id == key:
            return self.user
        return None

    async def execute(self, _statement):
        return FakeResult(value=self.scalar_value)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1


def _user(
    *,
    role: str = "superadmin",
    mfa_enabled: bool = False,
) -> User:
    return User(
        id=uuid.uuid4(),
        school_id=None,
        login="admin",
        email=None,
        password_hash="hash",
        role=role,
        first_name="Иван",
        last_name="Иванов",
        middle_name=None,
        phone=None,
        avatar="👤",
        locale="ru",
        timezone="Europe/Minsk",
        is_active=True,
        is_verified=True,
        must_change_password=False,
        mfa_enabled=mfa_enabled,
        mfa_secret_encrypted=None,
        mfa_pending_secret_encrypted=None,
        mfa_enrolled_at=None,
        mfa_last_used_counter=None,
        mfa_failed_attempts=0,
        mfa_locked_until=None,
        last_login_at=None,
        created_at=datetime.now(timezone.utc),
    )


def _override_session(session: FakeSession):
    async def override_session():
        yield session

    return override_session


def test_totp_and_recovery_code_helpers() -> None:
    secret = generate_totp_secret()
    at_time = 1_700_000_000.0
    code = totp_code(secret, at_time=at_time)

    assert verify_totp(secret, code, at_time=at_time) == int(at_time // 30)
    assert verify_totp(secret, "000000", at_time=at_time) is None
    assert decrypt_secret(encrypt_secret(secret)) == secret

    codes = generate_recovery_codes()
    assert len(codes) == 10
    assert all(len(code) == 19 for code in codes)
    assert hash_recovery_code(codes[0]) == hash_recovery_code(
        codes[0].replace("-", " ").upper()
    )
    assert hash_recovery_code(codes[0]) != hash_recovery_code(codes[1])


def test_mfa_token_has_its_own_type_and_purpose() -> None:
    user_id = uuid.uuid4()
    token, _expires_at = create_mfa_token(
        user_id=user_id,
        purpose=MFA_PURPOSE_VERIFY,
        ttl_seconds=60,
    )

    payload = decode_mfa_token(token, purpose=MFA_PURPOSE_VERIFY)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "mfa"

    with pytest.raises(TokenError):
        decode_mfa_token(token, purpose=MFA_PURPOSE_ENROLL)
    with pytest.raises(TokenError):
        decode_access_token(token)


@pytest.mark.asyncio
async def test_enrollment_and_totp_login() -> None:
    user = _user()
    session = FakeSession(user=user)
    secret, uri = await start_enrollment(session, user=user)

    assert secret
    assert uri.startswith("otpauth://totp/")
    assert user.mfa_pending_secret_encrypted
    assert decrypt_secret(user.mfa_pending_secret_encrypted) == secret

    now = time.time()
    codes = await complete_enrollment(
        session,
        user=user,
        code=totp_code(secret, at_time=now),
    )
    assert len(codes) == 10
    assert user.mfa_enabled is True
    assert user.mfa_secret_encrypted
    assert user.mfa_pending_secret_encrypted is None
    assert user.mfa_last_used_counter == int(now // 30)
    recovery_models = [
        item for item in session.added if isinstance(item, MfaRecoveryCode)
    ]
    assert len(recovery_models) == 10

    method = await verify_login_code(
        session,
        user=user,
        code=totp_code(secret, at_time=now + 30),
    )
    assert method == "totp"
    assert user.mfa_last_used_counter == int(now // 30) + 1


@pytest.mark.asyncio
async def test_invalid_mfa_code_increments_failures() -> None:
    user = _user(mfa_enabled=True)
    user.mfa_secret_encrypted = encrypt_secret(generate_totp_secret())
    session = FakeSession(user=user)

    with pytest.raises(MfaError):
        await verify_login_code(session, user=user, code="000000")
    assert user.mfa_failed_attempts == 1


def _refresh_token(
    user: User,
    *,
    raw_token: str = "refresh-token",
    mfa_verified: bool = False,
) -> RefreshToken:
    return RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked_at=None,
        mfa_verified=mfa_verified,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_refresh_rejects_superadmin_until_mfa_is_enrolled() -> None:
    user = _user()
    token = _refresh_token(user)
    session = FakeSession(user=user, scalar_value=token)

    with pytest.raises(AuthError, match="enrollment"):
        await rotate_refresh_token(session, raw_token="refresh-token")


@pytest.mark.asyncio
async def test_refresh_rejects_unverified_token_for_mfa_user() -> None:
    user = _user(mfa_enabled=True)
    token = _refresh_token(user, mfa_verified=False)
    session = FakeSession(user=user, scalar_value=token)

    with pytest.raises(AuthError, match="verification"):
        await rotate_refresh_token(session, raw_token="refresh-token")


@pytest.mark.asyncio
async def test_refresh_preserves_mfa_verified_flag() -> None:
    user = _user(mfa_enabled=True)
    token = _refresh_token(user, mfa_verified=True)
    session = FakeSession(user=user, scalar_value=token)

    _user_result, _raw_new, new_token = await rotate_refresh_token(
        session,
        raw_token="refresh-token",
    )

    assert token.revoked_at is not None
    assert new_token.mfa_verified is True


@pytest.mark.asyncio
async def test_login_returns_enrollment_challenge_for_superadmin(monkeypatch) -> None:
    user = _user()
    session = FakeSession(user=user)

    async def fake_authenticate(*_args, **_kwargs):
        return user

    monkeypatch.setattr(auth_api, "authenticate", fake_authenticate)
    app.dependency_overrides[get_session] = _override_session(session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"login": "admin", "password": "secret"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "mfa_enrollment_required"
    assert "access_token" not in payload
    assert payload["mfa_token"]
    assert payload["user"]["mfa_enabled"] is False


@pytest.mark.asyncio
async def test_login_returns_mfa_challenge_for_enabled_user(monkeypatch) -> None:
    user = _user(mfa_enabled=True)
    session = FakeSession(user=user)

    async def fake_authenticate(*_args, **_kwargs):
        return user

    monkeypatch.setattr(auth_api, "authenticate", fake_authenticate)
    app.dependency_overrides[get_session] = _override_session(session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"login": "admin", "password": "secret"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "mfa_required"
    assert "access_token" not in payload
    assert payload["mfa_token"]


@pytest.mark.asyncio
async def test_login_for_non_mfa_role_returns_tokens(monkeypatch) -> None:
    user = _user(role="teacher")
    session = FakeSession(user=user)

    async def fake_authenticate(*_args, **_kwargs):
        return user

    monkeypatch.setattr(auth_api, "authenticate", fake_authenticate)
    app.dependency_overrides[get_session] = _override_session(session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"login": "admin", "password": "secret"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["user"]["mfa_enabled"] is False


@pytest.mark.asyncio
async def test_full_enrollment_flow_returns_tokens_and_recovery_codes(monkeypatch) -> None:
    user = _user()
    session = FakeSession(user=user)

    async def fake_authenticate(*_args, **_kwargs):
        return user

    monkeypatch.setattr(auth_api, "authenticate", fake_authenticate)
    app.dependency_overrides[get_session] = _override_session(session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"login": "admin", "password": "secret"},
            )
            challenge = login.json()
            started = await client.post(
                "/api/v1/auth/mfa/enroll/start",
                json={"mfa_token": challenge["mfa_token"]},
            )
            secret = started.json()["secret"]
            completed = await client.post(
                "/api/v1/auth/mfa/enroll/verify",
                json={
                    "mfa_token": challenge["mfa_token"],
                    "code": totp_code(secret),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert started.status_code == 200
    assert completed.status_code == 200
    payload = completed.json()
    assert payload["access_token"]
    assert len(payload["recovery_codes"]) == 10
    assert payload["user"]["mfa_enabled"] is True
    assert user.mfa_enabled is True
    assert user.last_login_at is not None


@pytest.mark.asyncio
async def test_mfa_status_requires_authentication() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/auth/mfa/status")
    assert response.status_code == 401

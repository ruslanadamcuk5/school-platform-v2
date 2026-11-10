"""Emergency MFA reset service and CLI parser."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.db.mfa_admin import build_parser
from app.models.audit import AuditEvent
from app.models.iam import User
from app.services.mfa import MfaError, reset_mfa


class FakeResult:
    def __init__(self, value=None) -> None:
        self.value = value

    def scalar_one(self):
        return self.value


class ResetSession:
    def __init__(
        self,
        user: User,
        *,
        recovery_codes: int = 10,
        active_tokens: int = 2,
    ) -> None:
        self.user = user
        self.recovery_codes = recovery_codes
        self.active_tokens = active_tokens
        self.executed: list[object] = []
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement):
        self.executed.append(statement)
        if len(self.executed) == 1:
            return FakeResult(self.recovery_codes)
        if len(self.executed) == 2:
            return FakeResult(self.active_tokens)
        return FakeResult(0)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def _user() -> User:
    return User(
        id=uuid.uuid4(),
        school_id=None,
        login="admin",
        email=None,
        password_hash="hash",
        role="superadmin",
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
        mfa_enabled=True,
        mfa_secret_encrypted="encrypted-secret",
        mfa_pending_secret_encrypted="pending-secret",
        mfa_enrolled_at=datetime.now(timezone.utc),
        mfa_last_used_counter=123,
        mfa_failed_attempts=5,
        mfa_locked_until=datetime.now(timezone.utc) + timedelta(minutes=15),
        last_login_at=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_reset_mfa_clears_state_and_audits() -> None:
    user = _user()
    session = ResetSession(user)

    result = await reset_mfa(
        session,
        user=user,
        reason="lost TOTP device and recovery codes",
        actor="cli",
    )

    assert result.login == "admin"
    assert result.was_enabled is True
    assert result.recovery_codes_deleted == 10
    assert result.refresh_tokens_revoked == 2
    assert result.actor == "cli"

    assert user.mfa_enabled is False
    assert user.mfa_secret_encrypted is None
    assert user.mfa_pending_secret_encrypted is None
    assert user.mfa_enrolled_at is None
    assert user.mfa_last_used_counter is None
    assert user.mfa_failed_attempts == 0
    assert user.mfa_locked_until is None
    assert session.commits == 0

    audit_events = [
        item for item in session.added if isinstance(item, AuditEvent)
    ]
    assert len(audit_events) == 1
    event = audit_events[0]
    assert event.action == "mfa_reset"
    assert event.entity_type == "user"
    assert event.user_id is None
    assert event.details["source"] == "cli"
    assert event.details["target_login"] == "admin"
    assert event.details["recovery_codes_deleted"] == 10
    assert event.details["refresh_tokens_revoked"] == 2
    assert "encrypted-secret" not in str(event.details)


@pytest.mark.asyncio
async def test_reset_mfa_requires_reason() -> None:
    user = _user()
    session = ResetSession(user)

    with pytest.raises(MfaError, match="Reason"):
        await reset_mfa(session, user=user, reason="   ")

    assert session.executed == []
    assert user.mfa_enabled is True


def test_cli_requires_confirmation_and_reason() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["reset", "--login", "admin"])
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["reset", "--login", "admin", "--confirm", "admin"]
        )

    args = parser.parse_args(
        [
            "reset",
            "--login",
            "admin",
            "--confirm",
            "admin",
            "--reason",
            "lost TOTP device",
            "--dry-run",
        ]
    )
    assert args.command == "reset"
    assert args.dry_run is True
    assert args.allow_any_role is False

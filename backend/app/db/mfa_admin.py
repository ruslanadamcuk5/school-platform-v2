"""Emergency MFA administration CLI.

The command is intentionally local to the backend host and never exposes
TOTP secrets.  Use it only after a verified support request, with a reason
recorded in the immutable audit log.

Examples:
    PYTHONPATH=. python -m app.db.mfa_admin status --login admin
    PYTHONPATH=. python -m app.db.mfa_admin reset --login admin \
        --confirm admin --reason "lost TOTP device and recovery codes"
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.models.iam import RefreshToken, User
from app.services.mfa import MfaError, recovery_codes_remaining, reset_mfa


async def _find_user(session: AsyncSession, login: str) -> User | None:
    return (
        await session.execute(
            select(User).where(
                User.login == login,
                User.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()


async def _active_refresh_tokens(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    return int(
        (
            await session.execute(
                select(func.count())
                .select_from(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked_at.is_(None),
                )
            )
        ).scalar_one()
    )


async def _status(args: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as session:
        user = await _find_user(session, args.login)
        if user is None:
            print(f"ERROR: user not found: {args.login}", file=sys.stderr)
            return 2
        remaining = await recovery_codes_remaining(session, user_id=user.id)
        active_tokens = await _active_refresh_tokens(session, user.id)
        locked_until = (
            user.mfa_locked_until.isoformat()
            if user.mfa_locked_until is not None
            else "none"
        )
        print(
            f"login={user.login} role={user.role} "
            f"mfa_enabled={user.mfa_enabled} "
            f"recovery_codes_remaining={remaining} "
            f"refresh_tokens_active={active_tokens} "
            f"locked_until={locked_until}"
        )
        return 0


async def _reset(args: argparse.Namespace) -> int:
    if args.confirm != args.login:
        print(
            "ERROR: --confirm must repeat --login exactly",
            file=sys.stderr,
        )
        return 2
    reason = args.reason.strip()
    if len(reason) < 10:
        print(
            "ERROR: --reason must contain at least 10 characters",
            file=sys.stderr,
        )
        return 2

    async with AsyncSessionLocal() as session:
        user = await _find_user(session, args.login)
        if user is None:
            print(f"ERROR: user not found: {args.login}", file=sys.stderr)
            return 2
        if user.role != "superadmin" and not args.allow_any_role:
            print(
                "ERROR: reset is limited to superadmin; "
                "use --allow-any-role only for an approved procedure",
                file=sys.stderr,
            )
            return 2
        if args.dry_run:
            print(
                f"DRY-RUN login={user.login} role={user.role} "
                f"mfa_enabled={user.mfa_enabled} action=reset"
            )
            return 0

        try:
            result = await reset_mfa(
                session,
                user=user,
                reason=reason,
                actor="cli",
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise

        print(
            f"MFA reset: login={result.login} role={user.role} "
            f"was_enabled={result.was_enabled} "
            f"recovery_codes_deleted={result.recovery_codes_deleted} "
            f"refresh_tokens_revoked={result.refresh_tokens_revoked}"
        )
        print("Next login will require MFA enrollment.")
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser(
        "status",
        help="show MFA state without changing anything",
    )
    status.add_argument("--login", required=True)

    reset = subparsers.add_parser(
        "reset",
        help="clear MFA, delete recovery codes and revoke refresh sessions",
    )
    reset.add_argument("--login", required=True)
    reset.add_argument(
        "--confirm",
        required=True,
        help="repeat --login exactly to confirm the destructive action",
    )
    reset.add_argument(
        "--reason",
        required=True,
        help="support reason, at least 10 characters; stored in audit",
    )
    reset.add_argument(
        "--dry-run",
        action="store_true",
        help="show the target user without changing anything",
    )
    reset.add_argument(
        "--allow-any-role",
        action="store_true",
        help="allow reset for a non-superadmin after an approved procedure",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    try:
        if args.command == "status":
            return await _status(args)
        return await _reset(args)
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return asyncio.run(_run(args))
    except MfaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - operational guard
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

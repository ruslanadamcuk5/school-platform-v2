"""Idempotent seed for the pilot database.

Run from the backend directory:

    python -m app.db.seed

The script creates the pilot school, grades 1-11 and one superadmin account.
It never overwrites an existing user's password.
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.iam import User
from app.models.org import School, SchoolClass


async def seed() -> None:
    if not settings.admin_password:
        raise RuntimeError(
            "ADMIN_PASSWORD is not set. Add it to .env before running the seed."
        )

    async with AsyncSessionLocal() as session:
        school = (
            await session.execute(
                select(School).where(School.code == settings.seed_school_code)
            )
        ).scalar_one_or_none()
        if school is None:
            school = School(
                code=settings.seed_school_code,
                name=settings.seed_school_name,
                short_name="Пилотная школа",
                city=settings.seed_school_city,
                address="",
                is_active=True,
            )
            session.add(school)
            await session.flush()
            print(f"created school: {school.name} ({school.id})")
        else:
            print(f"school exists: {school.name} ({school.id})")

        existing_classes = (
            await session.execute(
                select(SchoolClass.grade, SchoolClass.letter).where(
                    SchoolClass.school_id == school.id,
                    SchoolClass.academic_year == settings.seed_academic_year,
                )
            )
        ).all()
        existing = {(grade, letter) for grade, letter in existing_classes}
        created_classes = 0
        for grade in range(1, 12):
            if (grade, "А") not in existing:
                session.add(
                    SchoolClass(
                        school_id=school.id,
                        grade=grade,
                        letter="А",
                        academic_year=settings.seed_academic_year,
                        is_active=True,
                    )
                )
                created_classes += 1
        print(f"classes created: {created_classes}")

        admin = (
            await session.execute(
                select(User).where(User.login == settings.admin_login)
            )
        ).scalar_one_or_none()
        if admin is None:
            admin = User(
                school_id=None,
                login=settings.admin_login,
                email=settings.admin_email or None,
                password_hash=hash_password(settings.admin_password),
                role="superadmin",
                first_name="Администратор",
                last_name="Платформы",
                is_active=True,
                is_verified=True,
            )
            session.add(admin)
            await session.flush()
            print(f"created superadmin: {admin.login} ({admin.id})")
        else:
            print(f"user exists, password unchanged: {admin.login} ({admin.id})")

        await session.commit()

    await engine.dispose()
    print("seed complete")


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    except Exception as exc:
        print(f"seed failed: {exc}", file=sys.stderr)
        raise

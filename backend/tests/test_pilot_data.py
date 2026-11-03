"""Regression tests for the synthetic pilot data helper."""

from __future__ import annotations

from app.db.pilot_data import _login_slug


def test_login_slug_transliterates_uppercase_and_separators() -> None:
    """Cyrillic titles must produce stable ASCII demo logins."""
    assert _login_slug("1А") == "1a"
    assert _login_slug("ИС-11") == "is.11"
    assert _login_slug("ЭК-21") == "ek.21"
    assert _login_slug("ПМИ-11") == "pmi.11"


def test_login_slug_keeps_existing_ascii_logins_idempotent() -> None:
    """Repairing an already-repaired demo login must not change it."""
    login = "demo.student.college.ek.21.10"
    assert _login_slug(login) == login
    assert _login_slug(_login_slug(login)) == login

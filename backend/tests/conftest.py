"""Shared test configuration.

Unit tests must not depend on a developer's local Redis instance.  The cache
module is reset and disabled before every test; ``test_cache.py`` injects a
fake client explicitly.
"""
from __future__ import annotations

import pytest

from app.core import cache as cache_module


@pytest.fixture(autouse=True)
def disable_redis_cache(monkeypatch):
    monkeypatch.setattr(cache_module.settings, "redis_url", None)
    cache_module.reset_cache_for_tests()
    yield
    cache_module.reset_cache_for_tests()

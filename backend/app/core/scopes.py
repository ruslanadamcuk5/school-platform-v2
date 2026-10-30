"""Organisational scope model shared by IAM groups and service activations.

The platform hierarchy is:

``country`` → ``region`` → ``city`` → ``school`` → ``class``.

The country level has no table because the platform serves one country.  A
fixed all-zero UUID is used as its scope identifier so that database
uniqueness constraints work uniformly for every level (PostgreSQL treats
``NULL`` values as distinct in unique indexes).
"""
from __future__ import annotations

import uuid

COUNTRY_SCOPE_ID = uuid.UUID(int=0)

SCOPE_TYPES = ("country", "region", "city", "school", "class")

# Larger value = more specific scope.  Used to resolve permission conflicts.
SCOPE_DEPTH = {
    "country": 0,
    "region": 1,
    "city": 2,
    "school": 3,
    "class": 4,
}

GROUP_CATEGORIES = (
    "students",
    "teachers",
    "administration",
    "methodologists",
    "psychologists",
    "secretaries",
    "parents",
    "other",
)

PERMISSION_EFFECTS = ("allow", "deny")

# Services that may never be switched off because the platform cannot operate
# without them (authentication, tenant structure, audit and the registry).
CORE_SERVICES = frozenset({"iam", "org", "system", "audit"})

SCOPE_TYPE_SQL = "scope_type IN ('country','region','city','school','class')"
GROUP_CATEGORY_SQL = (
    "category IN ('students','teachers','administration','methodologists',"
    "'psychologists','secretaries','parents','other')"
)
PERMISSION_EFFECT_SQL = "effect IN ('allow','deny')"

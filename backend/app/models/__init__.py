"""Domain models.

Importing this package registers every model on ``Base.metadata`` so Alembic
and the application see the complete schema.
"""
from app.models.audit import AuditEvent
from app.models.iam import RefreshToken, User
from app.models.org import ClassMembership, School, SchoolClass

__all__ = [
    "AuditEvent",
    "ClassMembership",
    "RefreshToken",
    "School",
    "SchoolClass",
    "User",
]

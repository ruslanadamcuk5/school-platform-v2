"""Shared response schemas."""
from __future__ import annotations

from pydantic import BaseModel


class Message(BaseModel):
    status: str = "ok"
    detail: str | None = None


class HealthOut(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    database: str
    jwt_ready: bool
    time: str

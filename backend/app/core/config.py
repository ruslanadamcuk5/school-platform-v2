"""Application settings.

Secrets are read from environment variables or from local ``.env`` files.
The project root ``.env`` is loaded first, then ``backend/.env`` can override
values for a server-side deployment.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_ROOT / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General
    app_name: str = "ВЕКТОР"
    app_env: str = "development"
    app_debug: bool = False
    app_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    api_version: str = "0.9.0"
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = (
        "postgresql+asyncpg://school_app:change-me@localhost:5432/school_platform"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_echo: bool = False

    # JWT
    jwt_algorithm: str = "RS256"
    jwt_access_ttl_minutes: int = 30
    jwt_refresh_ttl_days: int = 30
    jwt_private_key_path: str = "./secrets/jwt_private.pem"
    jwt_public_key_path: str = "./secrets/jwt_public.pem"
    jwt_issuer: str = "school-platform-v2"
    jwt_audience: str = "school-platform-clients"

    # CORS / security
    cors_origins: str = "http://localhost:5173,http://localhost:8000"
    rate_limit_enabled: bool = True
    audit_log_enabled: bool = True

    # Optional Redis cache. Empty REDIS_URL disables caching completely.
    redis_url: str | None = None
    redis_cache_ttl_seconds: int = 60
    redis_key_prefix: str = "school-platform"
    redis_socket_timeout_seconds: float = 1.0
    redis_failure_cooldown_seconds: float = 30.0

    # Initial seed. ADMIN_PASSWORD must be set before running the seed script.
    admin_login: str = "admin"
    admin_email: str = ""
    admin_password: str = ""
    seed_school_code: str = "pilot-school"
    seed_school_name: str = "Пилотная школа «ВЕКТОР»"
    seed_school_city: str = "Минск"
    seed_academic_year: str = "2026/2027"

    @model_validator(mode="after")
    def validate_redis_tls(self) -> Settings:
        """Remote Redis in pilot/production must use TLS.

        Loopback is allowed for local development even when the local ``.env``
        carries the pilot environment name.
        """
        if self.app_env.lower() in {"pilot", "production"} and self.redis_url:
            if not self.redis_url.startswith("rediss://"):
                host = (urlparse(self.redis_url).hostname or "").lower()
                if host not in {"localhost", "127.0.0.1", "::1"}:
                    raise ValueError(
                        "REDIS_URL must use rediss:// for remote hosts when "
                        "APP_ENV is pilot or production"
                    )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def access_token_ttl_seconds(self) -> int:
        return self.jwt_access_ttl_minutes * 60

    @property
    def refresh_token_ttl_seconds(self) -> int:
        return self.jwt_refresh_ttl_days * 24 * 60 * 60

    def resolve_path(self, raw_path: str) -> Path:
        """Resolve a relative path against the backend/project directories."""
        path = Path(raw_path).expanduser()
        if path.is_absolute():
            return path
        for base in (PROJECT_ROOT, BACKEND_DIR):
            candidate = (base / path).resolve()
            if candidate.exists():
                return candidate
        return (BACKEND_DIR / path).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

"""Application configuration loaded from environment variables.

All settings have safe local-development defaults so the backend boots without
any external services (SQLite instead of PostgreSQL, demo-mode AI, etc.).
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "CampusIQ"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    port: int = 8000

    # ---- Database ----
    database_url: str = "sqlite:///./campusiq.db"

    # ---- JWT ----
    jwt_secret: str = secrets.token_urlsafe(48)
    jwt_refresh_secret: str = secrets.token_urlsafe(48)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    secure_cookies: bool = False

    # ---- Password hashing ----
    password_hash_scheme: str = "bcrypt"

    # ---- Rate limiting ----
    rate_limit_enabled: bool = True
    rate_limit_default: str = "120/minute"
    rate_limit_login: str = "10/minute"
    rate_limit_ai: str = "30/minute"

    # ---- Uploads ----
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10
    allowed_upload_extensions: str = (
        "pdf,doc,docx,ppt,pptx,xls,xlsx,txt,zip,png,jpg,jpeg,webp"
    )

    # ---- Attendance policy ----
    attendance_threshold: float = 75.0
    attendance_warning_min: float = 65.0
    attendance_edit_window_hours: int = 48

    # ---- AI ----
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"
    ai_provider: str = "demo"  # openai | demo

    # ---- CORS ----
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://localhost:5173"

    # ---- Derived (computed in properties) ----
    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def sqlite_in_use(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [e.strip().lower().lstrip(".") for e in self.allowed_upload_extensions.split(",") if e.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @field_validator("database_url")
    @classmethod
    def _normalise_db_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            return "sqlite:///./campusiq.db"
        # Allow bare "postgres://..." to be upgraded to the psycopg3 driver.
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        if v.startswith("postgresql+psycopg2://"):
            return v.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Settings(BaseSettings):
    app_name: str = "Career Platform"
    app_env: str = "development"
    app_version: str = "0.1.0"
    database_url: str = "sqlite:///./career_platform.db"
    session_secret: str = "change-me-in-production"
    snapshot_path: str = "data/public-profile.json"
    admin_username: str = "admin"
    admin_password: str = "change-me-in-production"
    site_url: str = "http://127.0.0.1:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration comes from environment variables (12-factor).
    Defaults are for local development only."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "KudiReady API"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://kudi:kudi@localhost:5432/kudiready"

    jwt_secret: str = "dev-only-change-me-to-a-long-random-string"  # noqa: S105 — overridden by env in prod
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 12

    cors_origins: str = "http://localhost:5173"

    max_upload_bytes: int = 2 * 1024 * 1024
    max_rows_per_upload: int = 5000
    share_link_days: int = 14

    @field_validator("database_url")
    @classmethod
    def _normalise_db_url(cls, v: str) -> str:
        # Render/Heroku hand out postgres:// URLs; SQLAlchemy needs an explicit driver.
        if v.startswith("postgres://"):
            v = "postgresql+psycopg://" + v[len("postgres://") :]
        elif v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the API."""

    app_name: str = "Internship and Student Management API"
    debug: bool = False
    database_url: str = Field(
        default="sqlite:///./internship_management.db",
        min_length=1,
    )
    secret_key: str = Field(min_length=32)
    algorithm: str = Field(default="HS256", min_length=1)
    access_token_expire_minutes: int = Field(default=30, gt=0)

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: object) -> object:
        """Use psycopg 3 for PostgreSQL URLs supplied by hosting providers."""

        if isinstance(value, str):
            if value.startswith("postgres://"):
                return value.replace("postgres://", "postgresql+psycopg://", 1)
            if value.startswith("postgresql://"):
                return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> object:
        """Accept conventional environment names as well as boolean strings."""

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"production", "prod", "release"}:
                return False
            if normalized in {"development", "dev"}:
                return True
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()


settings = get_settings()

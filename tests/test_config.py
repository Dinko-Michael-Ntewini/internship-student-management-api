"""Tests for deployment-facing application configuration."""

from app.config import Settings


def test_render_postgresql_url_uses_psycopg_driver() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:password@host:5432/database",
        secret_key="x" * 32,
    )

    assert settings.database_url == (
        "postgresql+psycopg://user:password@host:5432/database"
    )


def test_legacy_postgres_url_uses_psycopg_driver() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgres://user:password@host:5432/database",
        secret_key="x" * 32,
    )

    assert settings.database_url == (
        "postgresql+psycopg://user:password@host:5432/database"
    )

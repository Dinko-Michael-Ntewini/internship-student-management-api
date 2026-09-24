"""Assertions that keep automated tests isolated from application data."""

from app.database import engine, get_db
from app.main import app
from tests.conftest import override_get_db, test_engine


def test_database_dependency_is_overridden_for_tests() -> None:
    assert app.dependency_overrides[get_db] is override_get_db
    assert test_engine is not engine
    assert str(test_engine.url) == "sqlite://"

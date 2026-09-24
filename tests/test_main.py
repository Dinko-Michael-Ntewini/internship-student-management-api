"""Foundation endpoint tests."""

from app.config import settings
from app.main import app


def test_application_imports() -> None:
    assert app.title == settings.app_name


def test_read_root(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Internship and Student Management API"}


def test_health_check(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_api_metadata_and_documentation_pages(client) -> None:
    assert app.title == "Internship and Student Management API"
    assert app.version == "2.0.0"
    assert "role-based access" in app.description

    openapi_response = client.get("/openapi.json")
    docs_response = client.get("/docs")
    redoc_response = client.get("/redoc")

    assert openapi_response.status_code == 200
    assert openapi_response.json()["info"]["version"] == "2.0.0"
    assert docs_response.status_code == 200
    assert "Swagger UI" in docs_response.text
    assert redoc_response.status_code == 200
    assert "ReDoc" in redoc_response.text

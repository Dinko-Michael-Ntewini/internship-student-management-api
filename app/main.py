"""FastAPI application entry point."""

from fastapi import FastAPI

from app.config import settings
from app.routes.applications import router as applications_router
from app.routes.auth import router as auth_router
from app.routes.students import router as students_router
from app.schemas.system import ApiInfoResponse, HealthResponse


tags_metadata = [
    {
        "name": "System",
        "description": "Public API information and service health endpoints.",
    },
    {
        "name": "Authentication",
        "description": "User registration, OAuth2 login, profiles, and role checks.",
    },
    {
        "name": "Students",
        "description": "Authenticated student management and student search.",
    },
    {
        "name": "Internship Applications",
        "description": "Authenticated application CRUD, status updates, search, and filtering.",
    },
]

app = FastAPI(
    title=settings.app_name,
    description=(
        "Secure backend for managing students and their internship applications, "
        "with role-based access, search, and filtering."
    ),
    version="2.0.0",
    debug=settings.debug,
    openapi_tags=tags_metadata,
)
app.include_router(auth_router)
app.include_router(students_router)
app.include_router(applications_router)


@app.get(
    "/",
    response_model=ApiInfoResponse,
    tags=["System"],
    summary="Get API information",
    description="Return the public name of the API.",
)
def read_root() -> ApiInfoResponse:
    """Return a simple API welcome message."""

    return ApiInfoResponse(message="Internship and Student Management API")


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Check API health",
    description="Return a lightweight service health response.",
)
def health_check() -> HealthResponse:
    """Expose a lightweight service health check."""

    return HealthResponse(status="healthy")

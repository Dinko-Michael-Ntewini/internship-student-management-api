"""Response schemas for public system endpoints."""

from pydantic import BaseModel


class ApiInfoResponse(BaseModel):
    """Public API information response."""

    message: str


class HealthResponse(BaseModel):
    """Public service health response."""

    status: str

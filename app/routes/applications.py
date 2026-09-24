"""Authenticated internship application management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user, require_role
from app.database import get_db
from app.models.internship_application import InternshipApplication
from app.models.user import User
from app.schemas.application import (
    InternshipApplicationCreate,
    InternshipApplicationFilters,
    InternshipApplicationPatch,
    InternshipApplicationResponse,
    InternshipApplicationStatusUpdate,
    InternshipApplicationUpdate,
)
from app.services import application_service


router = APIRouter(
    prefix="/applications",
    tags=["Internship Applications"],
    responses={
        401: {"description": "Missing, invalid, or expired token"},
        403: {"description": "Inactive user or insufficient permissions"},
    },
)
ApplicationId = Annotated[int, Path(gt=0)]
DatabaseSession = Annotated[Session, Depends(get_db)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(require_role("admin"))]


def _application_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Application not found",
    )


def _student_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Student not found",
    )


@router.post(
    "",
    response_model=InternshipApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an internship application",
    description="Create an application for an existing student. Administrator access is required.",
    responses={404: {"description": "Referenced student not found"}},
)
def create_application(
    application_data: InternshipApplicationCreate,
    db: DatabaseSession,
    _admin: AdminUser,
) -> InternshipApplication:
    """Create an internship application. Administrator access is required."""

    try:
        return application_service.create_application(db, application_data)
    except application_service.ApplicationStudentNotFoundError as exc:
        raise _student_not_found() from exc


@router.get(
    "",
    response_model=list[InternshipApplicationResponse],
    summary="List, search, and filter applications",
    description="Return applications matching optional search and filter query parameters.",
)
def list_applications(
    filters: Annotated[InternshipApplicationFilters, Query()],
    db: DatabaseSession,
    _user: ActiveUser,
) -> list[InternshipApplication]:
    """Search and filter applications for an active authenticated user."""

    return application_service.get_applications(db, filters)


@router.get(
    "/{application_id}",
    response_model=InternshipApplicationResponse,
    summary="Get an internship application",
    description="Return one application by positive integer ID.",
    responses={404: {"description": "Application not found"}},
)
def get_application(
    application_id: ApplicationId,
    db: DatabaseSession,
    _user: ActiveUser,
) -> InternshipApplication:
    """Return one application for an active authenticated user."""

    try:
        return application_service.get_application_by_id(db, application_id)
    except application_service.ApplicationNotFoundError as exc:
        raise _application_not_found() from exc


@router.put(
    "/{application_id}",
    response_model=InternshipApplicationResponse,
    summary="Replace an internship application",
    description="Replace all editable application fields. Administrator access is required.",
    responses={404: {"description": "Application or referenced student not found"}},
)
def replace_application(
    application_id: ApplicationId,
    application_data: InternshipApplicationUpdate,
    db: DatabaseSession,
    _admin: AdminUser,
) -> InternshipApplication:
    """Fully replace an application. Administrator access is required."""

    try:
        return application_service.update_application(
            db,
            application_id,
            application_data,
        )
    except application_service.ApplicationNotFoundError as exc:
        raise _application_not_found() from exc
    except application_service.ApplicationStudentNotFoundError as exc:
        raise _student_not_found() from exc


@router.patch(
    "/{application_id}",
    response_model=InternshipApplicationResponse,
    summary="Partially update an internship application",
    description="Update supplied application fields. Administrator access is required.",
    responses={404: {"description": "Application or referenced student not found"}},
)
def patch_application(
    application_id: ApplicationId,
    application_data: InternshipApplicationPatch,
    db: DatabaseSession,
    _admin: AdminUser,
) -> InternshipApplication:
    """Update selected application fields. Administrator access is required."""

    try:
        return application_service.partial_update_application(
            db,
            application_id,
            application_data,
        )
    except application_service.ApplicationNotFoundError as exc:
        raise _application_not_found() from exc
    except application_service.ApplicationStudentNotFoundError as exc:
        raise _student_not_found() from exc


@router.patch(
    "/{application_id}/status",
    response_model=InternshipApplicationResponse,
    summary="Update internship application status",
    description="Change only the application status. Administrator access is required.",
    responses={404: {"description": "Application not found"}},
)
def update_application_status(
    application_id: ApplicationId,
    status_data: InternshipApplicationStatusUpdate,
    db: DatabaseSession,
    _admin: AdminUser,
) -> InternshipApplication:
    """Update only the status. Administrator access is required."""

    try:
        return application_service.update_application_status(
            db,
            application_id,
            status_data,
        )
    except application_service.ApplicationNotFoundError as exc:
        raise _application_not_found() from exc


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an internship application",
    description="Delete an application. Administrator access is required.",
    responses={404: {"description": "Application not found"}},
)
def delete_application(
    application_id: ApplicationId,
    db: DatabaseSession,
    _admin: AdminUser,
) -> Response:
    """Delete an application. Administrator access is required."""

    try:
        application_service.delete_application(db, application_id)
    except application_service.ApplicationNotFoundError as exc:
        raise _application_not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

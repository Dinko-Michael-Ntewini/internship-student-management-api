"""Authenticated student-management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user, require_role
from app.database import get_db
from app.models.student import Student
from app.models.user import User
from app.schemas.student import (
    StudentCreate,
    StudentPatch,
    StudentResponse,
    StudentSearchParams,
    StudentUpdate,
)
from app.services import student_service


router = APIRouter(
    prefix="/students",
    tags=["Students"],
    responses={
        401: {"description": "Missing, invalid, or expired token"},
        403: {"description": "Inactive user or insufficient permissions"},
    },
)
StudentId = Annotated[int, Path(gt=0)]
DatabaseSession = Annotated[Session, Depends(get_db)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(require_role("admin"))]


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Student not found",
    )


def _duplicate_email() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Student email already registered",
    )


@router.post(
    "",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a student",
    description="Create a student record. Administrator access is required.",
    responses={409: {"description": "Student email already registered"}},
)
def create_student(
    student_data: StudentCreate,
    db: DatabaseSession,
    _admin: AdminUser,
) -> Student:
    """Create a student. Administrator access is required."""

    try:
        return student_service.create_student(db, student_data)
    except student_service.DuplicateStudentEmailError as exc:
        raise _duplicate_email() from exc


@router.get(
    "",
    response_model=list[StudentResponse],
    summary="List or search students",
    description="List students, optionally searching useful profile fields.",
)
def list_students(
    filters: Annotated[StudentSearchParams, Query()],
    db: DatabaseSession,
    _user: ActiveUser,
) -> list[Student]:
    """Search students for an active authenticated user."""

    return student_service.get_students(db, filters)


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Get a student",
    description="Return one student by positive integer ID.",
    responses={404: {"description": "Student not found"}},
)
def get_student(
    student_id: StudentId,
    db: DatabaseSession,
    _user: ActiveUser,
) -> Student:
    """Return one student for an active authenticated user."""

    try:
        return student_service.get_student_by_id(db, student_id)
    except student_service.StudentNotFoundError as exc:
        raise _not_found() from exc


@router.put(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Replace a student",
    description="Replace all editable student fields. Administrator access is required.",
    responses={
        404: {"description": "Student not found"},
        409: {"description": "Student email already registered"},
    },
)
def replace_student(
    student_id: StudentId,
    student_data: StudentUpdate,
    db: DatabaseSession,
    _admin: AdminUser,
) -> Student:
    """Replace all editable student data. Administrator access is required."""

    try:
        return student_service.update_student(db, student_id, student_data)
    except student_service.StudentNotFoundError as exc:
        raise _not_found() from exc
    except student_service.DuplicateStudentEmailError as exc:
        raise _duplicate_email() from exc


@router.patch(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Partially update a student",
    description="Update supplied student fields. Administrator access is required.",
    responses={
        404: {"description": "Student not found"},
        409: {"description": "Student email already registered"},
    },
)
def patch_student(
    student_id: StudentId,
    student_data: StudentPatch,
    db: DatabaseSession,
    _admin: AdminUser,
) -> Student:
    """Update selected student fields. Administrator access is required."""

    try:
        return student_service.partial_update_student(db, student_id, student_data)
    except student_service.StudentNotFoundError as exc:
        raise _not_found() from exc
    except student_service.DuplicateStudentEmailError as exc:
        raise _duplicate_email() from exc


@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a student",
    description="Delete a student and related applications. Administrator access is required.",
    responses={404: {"description": "Student not found"}},
)
def delete_student(
    student_id: StudentId,
    db: DatabaseSession,
    _admin: AdminUser,
) -> Response:
    """Delete a student. Administrator access is required."""

    try:
        student_service.delete_student(db, student_id)
    except student_service.StudentNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

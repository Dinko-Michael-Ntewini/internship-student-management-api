"""Database operations for internship application management."""

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.internship_application import InternshipApplication
from app.models.student import Student
from app.schemas.application import (
    InternshipApplicationCreate,
    InternshipApplicationFilters,
    InternshipApplicationPatch,
    InternshipApplicationStatusUpdate,
    InternshipApplicationUpdate,
)


class ApplicationNotFoundError(Exception):
    """Raised when a requested internship application does not exist."""


class ApplicationStudentNotFoundError(Exception):
    """Raised when an application references a missing student."""


def _ensure_student_exists(db: Session, student_id: int) -> None:
    if db.get(Student, student_id) is None:
        raise ApplicationStudentNotFoundError


def _commit(
    db: Session,
    application: InternshipApplication,
) -> InternshipApplication:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApplicationStudentNotFoundError from exc
    db.refresh(application)
    return application


def create_application(
    db: Session,
    application_data: InternshipApplicationCreate,
) -> InternshipApplication:
    """Create an application for an existing student."""

    _ensure_student_exists(db, application_data.student_id)
    application = InternshipApplication(**application_data.model_dump())
    db.add(application)
    return _commit(db, application)


def get_applications(
    db: Session,
    filters: InternshipApplicationFilters | None = None,
) -> list[InternshipApplication]:
    """Return applications matching optional search and filter criteria."""

    filters = filters or InternshipApplicationFilters()
    statement = select(InternshipApplication)
    if filters.search is not None:
        pattern = f"%{filters.search}%"
        statement = statement.where(
            or_(
                InternshipApplication.company_name.ilike(pattern),
                InternshipApplication.position.ilike(pattern),
                InternshipApplication.internship_type.ilike(pattern),
                InternshipApplication.location.ilike(pattern),
            )
        )
    if filters.status is not None:
        statement = statement.where(InternshipApplication.status == filters.status)
    for field_name in ("company_name", "position", "internship_type", "location"):
        value = getattr(filters, field_name)
        if value is not None:
            statement = statement.where(
                getattr(InternshipApplication, field_name).ilike(f"%{value}%")
            )
    if filters.student_id is not None:
        statement = statement.where(
            InternshipApplication.student_id == filters.student_id
        )
    statement = statement.order_by(InternshipApplication.id)
    return list(db.scalars(statement).all())


def get_application_by_id(
    db: Session,
    application_id: int,
) -> InternshipApplication:
    """Return one application or raise a domain-level not-found error."""

    application = db.get(InternshipApplication, application_id)
    if application is None:
        raise ApplicationNotFoundError
    return application


def update_application(
    db: Session,
    application_id: int,
    application_data: InternshipApplicationUpdate,
) -> InternshipApplication:
    """Replace all editable application fields."""

    application = get_application_by_id(db, application_id)
    _ensure_student_exists(db, application_data.student_id)
    for field, value in application_data.model_dump().items():
        setattr(application, field, value)
    return _commit(db, application)


def partial_update_application(
    db: Session,
    application_id: int,
    application_data: InternshipApplicationPatch,
) -> InternshipApplication:
    """Change only application fields supplied by the caller."""

    application = get_application_by_id(db, application_id)
    values = application_data.model_dump(exclude_unset=True)
    if "student_id" in values:
        _ensure_student_exists(db, values["student_id"])
    for field, value in values.items():
        setattr(application, field, value)
    return _commit(db, application)


def update_application_status(
    db: Session,
    application_id: int,
    status_data: InternshipApplicationStatusUpdate,
) -> InternshipApplication:
    """Change only an internship application's status."""

    application = get_application_by_id(db, application_id)
    application.status = status_data.status
    return _commit(db, application)


def delete_application(db: Session, application_id: int) -> None:
    """Delete an internship application."""

    application = get_application_by_id(db, application_id)
    db.delete(application)
    db.commit()

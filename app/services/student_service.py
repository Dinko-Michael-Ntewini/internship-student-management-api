"""Database operations for student management."""

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.student import Student
from app.schemas.student import (
    StudentCreate,
    StudentPatch,
    StudentSearchParams,
    StudentUpdate,
)


class StudentNotFoundError(Exception):
    """Raised when a requested student does not exist."""


class DuplicateStudentEmailError(Exception):
    """Raised when a student email is already in use."""


def _ensure_email_available(
    db: Session,
    email: str,
    excluded_student_id: int | None = None,
) -> None:
    statement = select(Student).where(func.lower(Student.email) == email.lower())
    if excluded_student_id is not None:
        statement = statement.where(Student.id != excluded_student_id)
    if db.scalar(statement) is not None:
        raise DuplicateStudentEmailError


def _commit(db: Session, student: Student) -> Student:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateStudentEmailError from exc
    db.refresh(student)
    return student


def create_student(db: Session, student_data: StudentCreate) -> Student:
    """Create and persist a student."""

    values = student_data.model_dump()
    values["email"] = str(student_data.email).lower()
    _ensure_email_available(db, values["email"])
    student = Student(**values)
    db.add(student)
    return _commit(db, student)


def get_students(
    db: Session,
    filters: StudentSearchParams | None = None,
) -> list[Student]:
    """Return students matching an optional case-insensitive text search."""

    filters = filters or StudentSearchParams()
    statement = select(Student)
    if filters.search is not None:
        pattern = f"%{filters.search}%"
        statement = statement.where(
            or_(
                Student.first_name.ilike(pattern),
                Student.last_name.ilike(pattern),
                Student.email.ilike(pattern),
                Student.university.ilike(pattern),
                Student.course.ilike(pattern),
            )
        )
    statement = statement.order_by(Student.id)
    return list(db.scalars(statement).all())


def get_student_by_id(db: Session, student_id: int) -> Student:
    """Return one student or raise a domain-level not-found error."""

    student = db.get(Student, student_id)
    if student is None:
        raise StudentNotFoundError
    return student


def update_student(
    db: Session,
    student_id: int,
    student_data: StudentUpdate,
) -> Student:
    """Replace all editable fields on a student."""

    student = get_student_by_id(db, student_id)
    values = student_data.model_dump()
    values["email"] = str(student_data.email).lower()
    _ensure_email_available(db, values["email"], excluded_student_id=student_id)
    for field, value in values.items():
        setattr(student, field, value)
    return _commit(db, student)


def partial_update_student(
    db: Session,
    student_id: int,
    student_data: StudentPatch,
) -> Student:
    """Change only the student fields supplied by the caller."""

    student = get_student_by_id(db, student_id)
    values = student_data.model_dump(exclude_unset=True)
    if "email" in values:
        values["email"] = str(values["email"]).lower()
        _ensure_email_available(
            db,
            values["email"],
            excluded_student_id=student_id,
        )
    for field, value in values.items():
        setattr(student, field, value)
    return _commit(db, student)


def delete_student(db: Session, student_id: int) -> None:
    """Delete a student or raise a domain-level not-found error."""

    student = get_student_by_id(db, student_id)
    db.delete(student)
    db.commit()

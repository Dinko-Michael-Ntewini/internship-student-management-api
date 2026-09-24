"""SQLAlchemy metadata and relationship tests."""

from sqlalchemy import inspect

from app.database import Base
from app.models import InternshipApplication, Student, User


def test_all_models_load_into_metadata() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "students",
        "internship_applications",
    }
    assert User.__tablename__ == "users"


def test_student_application_relationship_is_bidirectional() -> None:
    student_relationship = inspect(Student).relationships["internship_applications"]
    application_relationship = inspect(InternshipApplication).relationships["student"]

    assert student_relationship.uselist is True
    assert student_relationship.back_populates == "student"
    assert application_relationship.uselist is False
    assert application_relationship.back_populates == "internship_applications"


def test_application_student_foreign_key() -> None:
    student_id = InternshipApplication.__table__.c.student_id
    foreign_key = next(iter(student_id.foreign_keys))

    assert foreign_key.target_fullname == "students.id"

"""Database model exports.

Importing models here ensures Alembic can discover every table through Base.metadata.
"""

from app.models.internship_application import InternshipApplication
from app.models.student import Student
from app.models.user import User

__all__ = ["InternshipApplication", "Student", "User"]

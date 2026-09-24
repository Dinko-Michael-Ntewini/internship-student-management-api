"""Validation schemas for internship application management."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


ApplicationStatus = Literal["pending", "accepted", "rejected"]
PositiveStudentId = Annotated[int, Field(gt=0)]
LongText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
TypeText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]
NotesText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=5000),
]
FilterText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class InternshipApplicationFilters(BaseModel):
    """Validated query parameters for application search and filtering."""

    search: FilterText | None = None
    status: ApplicationStatus | None = None
    company_name: FilterText | None = None
    position: FilterText | None = None
    internship_type: FilterText | None = None
    location: FilterText | None = None
    student_id: PositiveStudentId | None = None

    model_config = ConfigDict(extra="forbid")


class InternshipApplicationCreate(BaseModel):
    """Input for creating an internship application."""

    student_id: PositiveStudentId
    company_name: LongText
    position: LongText
    internship_type: TypeText
    location: LongText
    status: ApplicationStatus = "pending"
    application_date: date
    notes: NotesText | None = None

    model_config = ConfigDict(extra="forbid")


class InternshipApplicationUpdate(BaseModel):
    """Input for fully replacing an internship application."""

    student_id: PositiveStudentId
    company_name: LongText
    position: LongText
    internship_type: TypeText
    location: LongText
    status: ApplicationStatus
    application_date: date
    notes: NotesText | None = None

    model_config = ConfigDict(extra="forbid")


class InternshipApplicationPatch(BaseModel):
    """Input for changing selected internship application fields."""

    student_id: PositiveStudentId | None = None
    company_name: LongText | None = None
    position: LongText | None = None
    internship_type: TypeText | None = None
    location: LongText | None = None
    status: ApplicationStatus | None = None
    application_date: date | None = None
    notes: NotesText | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            invalid_nulls = [
                field
                for field, value in data.items()
                if field != "notes" and value is None
            ]
            if invalid_nulls:
                raise ValueError("Required application fields cannot be null")
        return data


class InternshipApplicationStatusUpdate(BaseModel):
    """Input for changing only an application's status."""

    status: ApplicationStatus

    model_config = ConfigDict(extra="forbid")


class InternshipApplicationResponse(BaseModel):
    """Internship application data returned by the API."""

    id: int
    student_id: int
    company_name: str
    position: str
    internship_type: str
    location: str
    status: ApplicationStatus
    application_date: date
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

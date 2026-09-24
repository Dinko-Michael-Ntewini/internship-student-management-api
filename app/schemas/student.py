"""Validation schemas for student management."""

from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


NameText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
PhoneText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=30),
]
LongText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
LevelText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]
SearchText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class StudentSearchParams(BaseModel):
    """Validated query parameters for student search."""

    search: SearchText | None = None

    model_config = ConfigDict(extra="forbid")


class StudentData(BaseModel):
    """Fields required to create or fully replace a student."""

    first_name: NameText
    last_name: NameText
    email: EmailStr = Field(max_length=320)
    phone: PhoneText
    university: LongText
    course: LongText
    level: LevelText

    model_config = ConfigDict(extra="forbid")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, email: object) -> object:
        if isinstance(email, str):
            return email.strip().lower()
        return email


class StudentCreate(StudentData):
    """Input for creating a student."""


class StudentUpdate(StudentData):
    """Input for replacing all editable student fields."""


class StudentPatch(BaseModel):
    """Input for changing only selected student fields."""

    first_name: NameText | None = None
    last_name: NameText | None = None
    email: EmailStr | None = Field(default=None, max_length=320)
    phone: PhoneText | None = None
    university: LongText | None = None
    course: LongText | None = None
    level: LevelText | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_nulls(cls, data: object) -> object:
        if isinstance(data, dict) and any(value is None for value in data.values()):
            raise ValueError("Student fields cannot be null")
        return data

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, email: object) -> object:
        if isinstance(email, str):
            return email.strip().lower()
        return email


class StudentResponse(BaseModel):
    """Student data returned by the API."""

    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    university: str
    course: str
    level: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

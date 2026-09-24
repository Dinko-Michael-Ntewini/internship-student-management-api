"""Validation schemas for authentication endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    """Public registration input."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    model_config = ConfigDict(extra="forbid")

    @field_validator("password")
    @classmethod
    def validate_bcrypt_length(cls, password: str) -> str:
        """Reject passwords beyond bcrypt's 72-byte input limit."""

        if len(password.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return password


class UserResponse(BaseModel):
    """Safe user data returned by the API."""

    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """OAuth2-compatible access-token response."""

    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    """Simple success response."""

    message: str

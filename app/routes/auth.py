"""User registration, login, and protected account routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user, require_role
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse, TokenResponse, UserRegister, UserResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user",
    description="Create a normal user account with a securely hashed password.",
    responses={409: {"description": "Email already registered"}},
)
def register_user(
    registration: UserRegister,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Create a user while storing only a bcrypt password hash."""

    normalized_email = str(registration.email).lower()
    existing_user = db.scalar(
        select(User).where(func.lower(User.email) == normalized_email)
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=normalized_email,
        hashed_password=hash_password(registration.password),
        role="user",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from exc
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in for an access token",
    description="Validate OAuth2 form credentials and return a bearer JWT.",
    responses={
        401: {"description": "Incorrect email or password"},
        403: {"description": "Inactive user"},
    },
)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Validate OAuth2 form credentials and return a bearer token."""

    normalized_email = form_data.username.lower()
    user = db.scalar(select(User).where(func.lower(User.email) == normalized_email))
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current user",
    description="Return the active authenticated user's safe profile.",
    responses={
        401: {"description": "Missing, invalid, or expired token"},
        403: {"description": "Inactive user"},
    },
)
def read_current_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Return the authenticated user's safe profile."""

    return current_user


@router.get(
    "/admin-check",
    response_model=MessageResponse,
    summary="Verify administrator access",
    description="Confirm that the authenticated user has the admin role.",
    responses={
        401: {"description": "Missing, invalid, or expired token"},
        403: {"description": "Administrator role required"},
    },
)
def admin_check(
    _current_user: Annotated[User, Depends(require_role("admin"))],
) -> MessageResponse:
    """Demonstrate role-based authorization for administrators."""

    return MessageResponse(message="Admin access granted")

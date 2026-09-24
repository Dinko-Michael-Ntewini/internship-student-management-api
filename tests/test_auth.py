"""Registration, JWT authentication, and role authorization tests."""

from datetime import timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.main import app
from app.models.user import User


USER_EMAIL = "student@example.com"
USER_PASSWORD = "StrongPass123"


def register_user(
    client: TestClient,
    email: str = USER_EMAIL,
    password: str = USER_PASSWORD,
):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )


def login_user(
    client: TestClient,
    email: str = USER_EMAIL,
    password: str = USER_PASSWORD,
):
    return client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )


def bearer_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_successful_user_registration(
    client: TestClient,
    db_session: Session,
) -> None:
    response = register_user(client)
    stored_user = db_session.scalar(select(User).where(User.email == USER_EMAIL))

    assert response.status_code == 201
    assert response.json()["email"] == USER_EMAIL
    assert response.json()["role"] == "user"
    assert "hashed_password" not in response.json()
    assert stored_user is not None
    assert stored_user.role == "user"


def test_registration_cannot_create_admin(
    client: TestClient,
    db_session: Session,
) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "attacker@example.com",
            "password": USER_PASSWORD,
            "role": "admin",
        },
    )
    created_user = db_session.scalar(
        select(User).where(User.email == "attacker@example.com")
    )

    assert response.status_code == 422
    assert created_user is None


def test_duplicate_email_registration_fails(client: TestClient) -> None:
    register_user(client)
    response = register_user(client, email="STUDENT@example.com")

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


def test_password_is_hashed_before_storage(
    client: TestClient,
    db_session: Session,
) -> None:
    register_user(client)
    user = db_session.scalar(select(User).where(User.email == USER_EMAIL))

    assert user is not None
    assert user.hashed_password != USER_PASSWORD
    assert verify_password(USER_PASSWORD, user.hashed_password)


def test_registration_validates_email_and_password(client: TestClient) -> None:
    invalid_email = register_user(client, email="not-an-email")
    short_password = register_user(
        client,
        email="short@example.com",
        password="short",
    )
    oversized_bcrypt_password = register_user(
        client,
        email="unicode@example.com",
        password="\u00e9" * 36 + "x",
    )

    assert invalid_email.status_code == 422
    assert short_password.status_code == 422
    assert oversized_bcrypt_password.status_code == 422


def test_successful_login(client: TestClient) -> None:
    registered_user = register_user(client).json()
    response = login_user(client)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    token = response.json()["access_token"]
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
    )
    assert payload["sub"] == str(registered_user["id"])
    assert "exp" in payload


def test_incorrect_password_fails(client: TestClient) -> None:
    register_user(client)
    response = login_user(client, password="WrongPassword123")

    assert response.status_code == 401


def test_invalid_user_login_fails(client: TestClient) -> None:
    response = login_user(client, email="missing@example.com")

    assert response.status_code == 401


def test_me_without_token_fails(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_with_valid_token_returns_safe_profile(client: TestClient) -> None:
    register_user(client)
    token = login_user(client).json()["access_token"]
    response = client.get("/auth/me", headers=bearer_header(token))

    assert response.status_code == 200
    assert response.json()["email"] == USER_EMAIL
    assert "hashed_password" not in response.json()


def test_invalid_token_fails(client: TestClient) -> None:
    response = client.get("/auth/me", headers=bearer_header("not-a-valid-jwt"))

    assert response.status_code == 401


def test_expired_token_fails(client: TestClient) -> None:
    register_response = register_user(client)
    expired_token = create_access_token(
        str(register_response.json()["id"]),
        expires_delta=timedelta(minutes=-1),
    )
    response = client.get("/auth/me", headers=bearer_header(expired_token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_admin_route_rejects_normal_user(client: TestClient) -> None:
    register_user(client)
    token = login_user(client).json()["access_token"]
    response = client.get("/auth/admin-check", headers=bearer_header(token))

    assert response.status_code == 403


def test_admin_route_accepts_directly_provisioned_admin(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_password = "AdminPass123"
    admin = User(
        email="admin@example.com",
        hashed_password=hash_password(admin_password),
        role="admin",
    )
    db_session.add(admin)
    db_session.commit()

    assert admin.hashed_password != admin_password
    assert verify_password(admin_password, admin.hashed_password)
    token = login_user(
        client,
        email=admin.email,
        password=admin_password,
    ).json()["access_token"]
    response = client.get("/auth/admin-check", headers=bearer_header(token))

    assert response.status_code == 200
    assert response.json() == {"message": "Admin access granted"}


def test_inactive_user_is_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    register_user(client)
    user = db_session.scalar(select(User).where(User.email == USER_EMAIL))
    assert user is not None
    user.is_active = False
    db_session.commit()

    login_response = login_user(client)
    token = create_access_token(str(user.id))
    profile_response = client.get("/auth/me", headers=bearer_header(token))

    assert login_response.status_code == 403
    assert profile_response.status_code == 403


def test_openapi_configures_oauth2_for_protected_routes() -> None:
    schema = app.openapi()
    password_flow = schema["components"]["securitySchemes"][
        "OAuth2PasswordBearer"
    ]["flows"]["password"]
    registration_schema = schema["components"]["schemas"]["UserRegister"]

    assert password_flow["tokenUrl"] == "auth/login"
    assert schema["paths"]["/auth/me"]["get"]["security"] == [
        {"OAuth2PasswordBearer": []}
    ]
    assert "role" not in registration_schema["properties"]
    assert registration_schema["additionalProperties"] is False

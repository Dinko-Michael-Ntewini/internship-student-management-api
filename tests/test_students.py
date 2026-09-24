"""Student CRUD, validation, authentication, and authorization tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.user import User
from app.schemas.student import StudentCreate
from app.services import student_service


STUDENT_DATA = {
    "first_name": "Ama",
    "last_name": "Mensah",
    "email": "ama.mensah@example.com",
    "phone": "+233201234567",
    "university": "University of Ghana",
    "course": "Computer Science",
    "level": "300",
}


def create_auth_headers(
    client: TestClient,
    db: Session,
    role: str,
) -> dict[str, str]:
    email = f"{role}@example.com"
    password = f"{role.title()}Pass123"
    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    login = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def seed_student(db: Session, **changes: str):
    data = {**STUDENT_DATA, **changes}
    return student_service.create_student(db, StudentCreate(**data))


def test_authenticated_user_can_list_students(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "user")
    seed_student(db_session)
    seed_student(db_session, email="second@example.com", first_name="Kojo")

    response = client.get("/students", headers=headers)

    assert response.status_code == 200
    assert [student["first_name"] for student in response.json()] == ["Ama", "Kojo"]


def test_authenticated_user_can_get_one_student(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "user")
    student = seed_student(db_session)

    response = client.get(f"/students/{student.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["email"] == STUDENT_DATA["email"]


def test_nonexistent_student_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "user")

    response = client.get("/students/999", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Student not found"


@pytest.mark.parametrize("student_id", [0, -1])
def test_invalid_student_id_returns_422(
    client: TestClient,
    db_session: Session,
    student_id: int,
) -> None:
    headers = create_auth_headers(client, db_session, "user")

    response = client.get(f"/students/{student_id}", headers=headers)

    assert response.status_code == 422


def test_admin_can_create_student(client: TestClient, db_session: Session) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    payload = {**STUDENT_DATA, "first_name": "  Ama  ", "email": "AMA.MENSAH@EXAMPLE.COM"}

    response = client.post("/students", headers=headers, json=payload)

    assert response.status_code == 201
    assert response.json()["first_name"] == "Ama"
    assert response.json()["email"] == STUDENT_DATA["email"]
    assert response.json()["id"] > 0


def test_duplicate_student_email_fails(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    first_response = client.post("/students", headers=headers, json=STUDENT_DATA)
    duplicate = {**STUDENT_DATA, "email": "AMA.MENSAH@example.com"}

    duplicate_response = client.post("/students", headers=headers, json=duplicate)

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == "Student email already registered"


def test_invalid_email_and_blank_fields_fail(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    invalid_email = client.post(
        "/students",
        headers=headers,
        json={**STUDENT_DATA, "email": "not-an-email"},
    )
    blank_phone = client.post(
        "/students",
        headers=headers,
        json={**STUDENT_DATA, "email": "other@example.com", "phone": "   "},
    )

    assert invalid_email.status_code == 422
    assert blank_phone.status_code == 422


def test_put_fully_updates_student(client: TestClient, db_session: Session) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)
    replacement = {
        "first_name": "Akosua",
        "last_name": "Owusu",
        "email": "akosua.owusu@example.com",
        "phone": "+233241111111",
        "university": "KNUST",
        "course": "Information Technology",
        "level": "400",
    }

    response = client.put(
        f"/students/{student.id}",
        headers=headers,
        json=replacement,
    )

    assert response.status_code == 200
    for field, value in replacement.items():
        assert response.json()[field] == value


def test_put_requires_complete_student_data(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)

    response = client.put(
        f"/students/{student.id}",
        headers=headers,
        json={"course": "Data Science"},
    )

    assert response.status_code == 422


def test_patch_updates_only_supplied_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)

    response = client.patch(
        f"/students/{student.id}",
        headers=headers,
        json={"course": "Data Science", "level": "400"},
    )

    assert response.status_code == 200
    assert response.json()["course"] == "Data Science"
    assert response.json()["level"] == "400"
    assert response.json()["first_name"] == STUDENT_DATA["first_name"]
    assert response.json()["email"] == STUDENT_DATA["email"]


def test_patch_duplicate_email_fails(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    first = seed_student(db_session)
    second = seed_student(db_session, email="second@example.com")

    response = client.patch(
        f"/students/{second.id}",
        headers=headers,
        json={"email": first.email.upper()},
    )

    assert response.status_code == 409


def test_delete_student_and_retrieval_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)

    delete_response = client.delete(f"/students/{student.id}", headers=headers)
    get_response = client.get(f"/students/{student.id}", headers=headers)

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert get_response.status_code == 404


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/students", None),
        ("GET", "/students/1", None),
        ("POST", "/students", STUDENT_DATA),
        ("PUT", "/students/1", STUDENT_DATA),
        ("PATCH", "/students/1", {"level": "400"}),
        ("DELETE", "/students/1", None),
    ],
)
def test_student_routes_require_authentication(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, str] | None,
) -> None:
    response = client.request(method, path, json=payload)

    assert response.status_code == 401


def test_inactive_user_cannot_read_students(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "user")
    user = db_session.scalar(select(User).where(User.email == "user@example.com"))
    assert user is not None
    user.is_active = False
    db_session.commit()

    response = client.get("/students", headers=headers)

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("POST", "/students", STUDENT_DATA),
        ("PUT", "/students/1", STUDENT_DATA),
        ("PATCH", "/students/1", {"level": "400"}),
        ("DELETE", "/students/1", None),
    ],
)
def test_normal_user_cannot_modify_students(
    client: TestClient,
    db_session: Session,
    method: str,
    path: str,
    payload: dict[str, str] | None,
) -> None:
    headers = create_auth_headers(client, db_session, "user")
    seed_student(db_session)

    response = client.request(method, path, headers=headers, json=payload)

    assert response.status_code == 403


def test_update_and_delete_missing_student_return_404(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")

    put_response = client.put(
        "/students/999",
        headers=headers,
        json=STUDENT_DATA,
    )
    patch_response = client.patch(
        "/students/999",
        headers=headers,
        json={"level": "400"},
    )
    delete_response = client.delete("/students/999", headers=headers)

    assert put_response.status_code == 404
    assert patch_response.status_code == 404
    assert delete_response.status_code == 404


def test_openapi_exposes_protected_student_crud() -> None:
    schema = app.openapi()

    assert "/students" in schema["paths"]
    assert "/students/{student_id}" in schema["paths"]
    assert set(schema["paths"]["/students"]) == {"get", "post"}
    assert set(schema["paths"]["/students/{student_id}"]) == {
        "get",
        "put",
        "patch",
        "delete",
    }
    for path_item in (
        schema["paths"]["/students"],
        schema["paths"]["/students/{student_id}"],
    ):
        for operation in path_item.values():
            assert operation["security"] == [{"OAuth2PasswordBearer": []}]

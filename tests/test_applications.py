"""Internship application CRUD, relationship, auth, and validation tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.user import User
from app.schemas.application import InternshipApplicationCreate
from app.schemas.student import StudentCreate
from app.services import application_service, student_service


STUDENT_DATA = {
    "first_name": "Ama",
    "last_name": "Mensah",
    "email": "ama.applications@example.com",
    "phone": "+233201234567",
    "university": "University of Ghana",
    "course": "Computer Science",
    "level": "300",
}
APPLICATION_DATA = {
    "company_name": "Example Technologies",
    "position": "Backend Intern",
    "internship_type": "On-site",
    "location": "Accra",
    "status": "pending",
    "application_date": "2026-10-01",
    "notes": "Submitted through the careers portal.",
}


def create_auth_headers(
    client: TestClient,
    db: Session,
    role: str,
) -> dict[str, str]:
    email = f"applications-{role}@example.com"
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
    return student_service.create_student(
        db,
        StudentCreate(**{**STUDENT_DATA, **changes}),
    )


def seed_application(db: Session, student_id: int, **changes: object):
    data = {**APPLICATION_DATA, "student_id": student_id, **changes}
    return application_service.create_application(
        db,
        InternshipApplicationCreate(**data),
    )


def application_payload(student_id: int, **changes: object) -> dict[str, object]:
    return {**APPLICATION_DATA, "student_id": student_id, **changes}


def test_authenticated_user_can_list_applications(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "user")
    student = seed_student(db_session)
    seed_application(db_session, student.id)
    seed_application(db_session, student.id, company_name="Second Company")

    response = client.get("/applications", headers=headers)

    assert response.status_code == 200
    assert [item["company_name"] for item in response.json()] == [
        "Example Technologies",
        "Second Company",
    ]


def test_authenticated_user_can_get_application(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "user")
    student = seed_student(db_session)
    internship_application = seed_application(db_session, student.id)

    response = client.get(
        f"/applications/{internship_application.id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["student_id"] == student.id
    assert response.json()["status"] == "pending"


def test_nonexistent_application_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "user")

    response = client.get("/applications/999", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found"


@pytest.mark.parametrize("application_id", [0, -1])
def test_invalid_application_id_returns_422(
    client: TestClient,
    db_session: Session,
    application_id: int,
) -> None:
    headers = create_auth_headers(client, db_session, "user")

    response = client.get(f"/applications/{application_id}", headers=headers)

    assert response.status_code == 422


def test_admin_can_create_application(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)

    response = client.post(
        "/applications",
        headers=headers,
        json=application_payload(student.id, company_name="  Example Technologies  "),
    )

    assert response.status_code == 201
    assert response.json()["student_id"] == student.id
    assert response.json()["company_name"] == "Example Technologies"
    assert response.json()["status"] == "pending"


def test_create_with_nonexistent_student_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")

    response = client.post(
        "/applications",
        headers=headers,
        json=application_payload(999),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Student not found"


def test_application_input_validation(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)

    invalid_student_id = client.post(
        "/applications",
        headers=headers,
        json=application_payload(0),
    )
    invalid_status = client.post(
        "/applications",
        headers=headers,
        json=application_payload(student.id, status="interviewing"),
    )
    blank_company = client.post(
        "/applications",
        headers=headers,
        json=application_payload(student.id, company_name="   "),
    )
    invalid_date = client.post(
        "/applications",
        headers=headers,
        json=application_payload(student.id, application_date="not-a-date"),
    )

    assert invalid_student_id.status_code == 422
    assert invalid_status.status_code == 422
    assert blank_company.status_code == 422
    assert invalid_date.status_code == 422


def test_put_fully_updates_application_and_student_relationship(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    first_student = seed_student(db_session)
    second_student = seed_student(
        db_session,
        email="second.student@example.com",
        first_name="Kojo",
    )
    internship_application = seed_application(db_session, first_student.id)
    replacement = application_payload(
        second_student.id,
        company_name="Updated Company",
        position="Software Engineering Intern",
        internship_type="Hybrid",
        location="Kumasi",
        status="accepted",
        application_date="2026-11-15",
        notes=None,
    )

    response = client.put(
        f"/applications/{internship_application.id}",
        headers=headers,
        json=replacement,
    )

    assert response.status_code == 200
    assert response.json()["student_id"] == second_student.id
    assert response.json()["company_name"] == "Updated Company"
    assert response.json()["status"] == "accepted"
    assert response.json()["notes"] is None


def test_put_missing_application_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)

    response = client.put(
        "/applications/999",
        headers=headers,
        json=application_payload(student.id),
    )

    assert response.status_code == 404


def test_put_requires_complete_application_data(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)
    internship_application = seed_application(db_session, student.id)

    response = client.put(
        f"/applications/{internship_application.id}",
        headers=headers,
        json={"status": "accepted"},
    )

    assert response.status_code == 422


def test_put_with_nonexistent_student_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)
    internship_application = seed_application(db_session, student.id)

    response = client.put(
        f"/applications/{internship_application.id}",
        headers=headers,
        json=application_payload(999),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Student not found"


def test_patch_updates_only_supplied_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)
    internship_application = seed_application(db_session, student.id)

    response = client.patch(
        f"/applications/{internship_application.id}",
        headers=headers,
        json={"position": "Platform Engineering Intern", "notes": None},
    )

    assert response.status_code == 200
    assert response.json()["position"] == "Platform Engineering Intern"
    assert response.json()["notes"] is None
    assert response.json()["company_name"] == APPLICATION_DATA["company_name"]
    assert response.json()["status"] == "pending"


def test_patch_with_nonexistent_student_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)
    internship_application = seed_application(db_session, student.id)

    response = client.patch(
        f"/applications/{internship_application.id}",
        headers=headers,
        json={"student_id": 999},
    )

    assert response.status_code == 404


def test_patch_and_status_update_missing_application_return_404(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")

    patch_response = client.patch(
        "/applications/999",
        headers=headers,
        json={"location": "Kumasi"},
    )
    status_response = client.patch(
        "/applications/999/status",
        headers=headers,
        json={"status": "accepted"},
    )

    assert patch_response.status_code == 404
    assert status_response.status_code == 404


def test_status_update_changes_only_status(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)
    internship_application = seed_application(db_session, student.id)

    response = client.patch(
        f"/applications/{internship_application.id}/status",
        headers=headers,
        json={"status": "accepted"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert response.json()["company_name"] == APPLICATION_DATA["company_name"]
    assert response.json()["student_id"] == student.id


def test_status_update_rejects_invalid_status(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)
    internship_application = seed_application(db_session, student.id)

    response = client.patch(
        f"/applications/{internship_application.id}/status",
        headers=headers,
        json={"status": "interviewing"},
    )

    assert response.status_code == 422


def test_delete_application_and_retrieval_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")
    student = seed_student(db_session)
    internship_application = seed_application(db_session, student.id)

    delete_response = client.delete(
        f"/applications/{internship_application.id}",
        headers=headers,
    )
    get_response = client.get(
        f"/applications/{internship_application.id}",
        headers=headers,
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert get_response.status_code == 404


def test_delete_missing_application_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = create_auth_headers(client, db_session, "admin")

    response = client.delete("/applications/999", headers=headers)

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/applications", None),
        ("GET", "/applications/1", None),
        ("POST", "/applications", application_payload(1)),
        ("PUT", "/applications/1", application_payload(1)),
        ("PATCH", "/applications/1", {"location": "Kumasi"}),
        ("PATCH", "/applications/1/status", {"status": "accepted"}),
        ("DELETE", "/applications/1", None),
    ],
)
def test_application_routes_require_authentication(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    response = client.request(method, path, json=payload)

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "path_suffix", "payload"),
    [
        ("POST", "", None),
        ("PUT", "/{id}", None),
        ("PATCH", "/{id}", {"location": "Kumasi"}),
        ("PATCH", "/{id}/status", {"status": "accepted"}),
        ("DELETE", "/{id}", None),
    ],
)
def test_normal_user_cannot_modify_applications(
    client: TestClient,
    db_session: Session,
    method: str,
    path_suffix: str,
    payload: dict[str, object] | None,
) -> None:
    headers = create_auth_headers(client, db_session, "user")
    student = seed_student(db_session)
    internship_application = seed_application(db_session, student.id)
    path = "/applications" + path_suffix.format(id=internship_application.id)
    request_payload = payload
    if method in {"POST", "PUT"}:
        request_payload = application_payload(student.id)

    response = client.request(
        method,
        path,
        headers=headers,
        json=request_payload,
    )

    assert response.status_code == 403


def test_one_student_can_have_multiple_applications(db_session: Session) -> None:
    student = seed_student(db_session)
    first = seed_application(db_session, student.id)
    second = seed_application(
        db_session,
        student.id,
        company_name="Second Company",
    )
    db_session.refresh(student)

    application_ids = {item.id for item in student.internship_applications}

    assert application_ids == {first.id, second.id}
    assert first.student_id == student.id
    assert second.student_id == student.id


def test_deleting_student_cascades_to_applications(db_session: Session) -> None:
    student = seed_student(db_session)
    internship_application = seed_application(db_session, student.id)

    student_service.delete_student(db_session, student.id)

    with pytest.raises(application_service.ApplicationNotFoundError):
        application_service.get_application_by_id(
            db_session,
            internship_application.id,
        )


def test_openapi_exposes_protected_application_crud_and_status_route() -> None:
    schema = app.openapi()

    assert set(schema["paths"]["/applications"]) == {"get", "post"}
    assert set(schema["paths"]["/applications/{application_id}"]) == {
        "get",
        "put",
        "patch",
        "delete",
    }
    status_operation = schema["paths"][
        "/applications/{application_id}/status"
    ]["patch"]
    assert status_operation["summary"] == "Update internship application status"
    for path in (
        "/applications",
        "/applications/{application_id}",
        "/applications/{application_id}/status",
    ):
        for operation in schema["paths"][path].values():
            assert operation["security"] == [{"OAuth2PasswordBearer": []}]

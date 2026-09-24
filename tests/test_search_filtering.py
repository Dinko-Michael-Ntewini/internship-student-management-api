"""Application filtering, text search, and student search tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.user import User
from app.schemas.application import InternshipApplicationCreate
from app.schemas.student import StudentCreate
from app.services import application_service, student_service


def auth_headers(client: TestClient, db: Session) -> dict[str, str]:
    email = "search-user@example.com"
    password = "SearchPass123"
    db.add(
        User(
            email=email,
            hashed_password=hash_password(password),
            role="user",
        )
    )
    db.commit()
    login = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def seed_search_records(db: Session) -> tuple[int, int]:
    first_student = student_service.create_student(
        db,
        StudentCreate(
            first_name="Ama",
            last_name="Mensah",
            email="ama.search@example.com",
            phone="0201111111",
            university="University of Ghana",
            course="Computer Science",
            level="300",
        ),
    )
    second_student = student_service.create_student(
        db,
        StudentCreate(
            first_name="Kojo",
            last_name="Asare",
            email="kojo.search@example.com",
            phone="0202222222",
            university="KNUST",
            course="Mechanical Engineering",
            level="400",
        ),
    )
    records = [
        {
            "student_id": first_student.id,
            "company_name": "Google Ghana",
            "position": "Software Engineering Intern",
            "internship_type": "Hybrid",
            "location": "Accra",
            "status": "pending",
            "application_date": "2026-10-01",
        },
        {
            "student_id": first_student.id,
            "company_name": "Microsoft Africa",
            "position": "Data Analyst Intern",
            "internship_type": "Remote",
            "location": "Kumasi",
            "status": "accepted",
            "application_date": "2026-10-02",
        },
        {
            "student_id": second_student.id,
            "company_name": "LocalTech",
            "position": "Software Support Intern",
            "internship_type": "On-site",
            "location": "Accra",
            "status": "rejected",
            "application_date": "2026-10-03",
        },
    ]
    for record in records:
        application_service.create_application(
            db,
            InternshipApplicationCreate(**record),
        )
    return first_student.id, second_student.id


def company_names(response) -> list[str]:
    assert response.status_code == 200
    return [item["company_name"] for item in response.json()]


def test_search_applications_by_company(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = auth_headers(client, db_session)
    seed_search_records(db_session)

    response = client.get(
        "/applications",
        params={"search": "google"},
        headers=headers,
    )

    assert company_names(response) == ["Google Ghana"]


def test_search_applications_by_position(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = auth_headers(client, db_session)
    seed_search_records(db_session)

    response = client.get(
        "/applications",
        params={"search": "data analyst"},
        headers=headers,
    )

    assert company_names(response) == ["Microsoft Africa"]


def test_application_search_is_case_insensitive(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = auth_headers(client, db_session)
    seed_search_records(db_session)

    response = client.get(
        "/applications",
        params={"search": "SOFTWARE"},
        headers=headers,
    )

    assert company_names(response) == ["Google Ghana", "LocalTech"]


@pytest.mark.parametrize(
    ("query", "expected_companies"),
    [
        ({"status": "accepted"}, ["Microsoft Africa"]),
        ({"location": "aCcRa"}, ["Google Ghana", "LocalTech"]),
        ({"internship_type": "remote"}, ["Microsoft Africa"]),
        ({"company_name": "MICRO"}, ["Microsoft Africa"]),
        ({"position": "support"}, ["LocalTech"]),
    ],
)
def test_application_text_and_status_filters(
    client: TestClient,
    db_session: Session,
    query: dict[str, str],
    expected_companies: list[str],
) -> None:
    headers = auth_headers(client, db_session)
    seed_search_records(db_session)

    response = client.get("/applications", params=query, headers=headers)

    assert company_names(response) == expected_companies


def test_filter_applications_by_student_id(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = auth_headers(client, db_session)
    first_student_id, _ = seed_search_records(db_session)

    response = client.get(
        "/applications",
        params={"student_id": first_student_id},
        headers=headers,
    )

    assert company_names(response) == ["Google Ghana", "Microsoft Africa"]


def test_combined_application_filters(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = auth_headers(client, db_session)
    seed_search_records(db_session)

    response = client.get(
        "/applications",
        params={"status": "rejected", "location": "accra"},
        headers=headers,
    )

    assert company_names(response) == ["LocalTech"]


def test_search_and_filter_together(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = auth_headers(client, db_session)
    seed_search_records(db_session)

    response = client.get(
        "/applications",
        params={"search": "software", "status": "pending"},
        headers=headers,
    )

    assert company_names(response) == ["Google Ghana"]


def test_no_application_matches_returns_empty_list(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = auth_headers(client, db_session)
    seed_search_records(db_session)

    response = client.get(
        "/applications",
        params={"search": "no-such-company"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    "query",
    [
        {"status": "interviewing"},
        {"student_id": 0},
        {"student_id": -1},
        {"search": "   "},
    ],
)
def test_invalid_application_query_parameters_return_422(
    client: TestClient,
    db_session: Session,
    query: dict[str, str | int],
) -> None:
    headers = auth_headers(client, db_session)

    response = client.get("/applications", params=query, headers=headers)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("search", "expected_email"),
    [
        ("ama", "ama.search@example.com"),
        ("MENSAH", "ama.search@example.com"),
        ("university of ghana", "ama.search@example.com"),
        ("mechanical", "kojo.search@example.com"),
    ],
)
def test_student_search_is_case_insensitive_across_useful_fields(
    client: TestClient,
    db_session: Session,
    search: str,
    expected_email: str,
) -> None:
    headers = auth_headers(client, db_session)
    seed_search_records(db_session)

    response = client.get(
        "/students",
        params={"search": search},
        headers=headers,
    )

    assert response.status_code == 200
    assert [student["email"] for student in response.json()] == [expected_email]


def test_search_query_parameters_are_documented_and_protected() -> None:
    schema = app.openapi()
    application_parameters = {
        parameter["name"]: parameter
        for parameter in schema["paths"]["/applications"]["get"]["parameters"]
    }

    assert set(application_parameters) == {
        "search",
        "status",
        "company_name",
        "position",
        "internship_type",
        "location",
        "student_id",
    }
    status_schema = str(application_parameters["status"]["schema"])
    for allowed_status in ("pending", "accepted", "rejected"):
        assert allowed_status in status_schema
    assert schema["paths"]["/applications"]["get"]["security"] == [
        {"OAuth2PasswordBearer": []}
    ]
    student_parameters = schema["paths"]["/students"]["get"]["parameters"]
    assert [parameter["name"] for parameter in student_parameters] == ["search"]

# Internship and Student Management Production API

This repository contains a production-ready FastAPI backend for managing students and internship applications. API version `2.0.0` provides secure JWT authentication, role authorization, CRUD operations, search and filtering, database migrations, and an isolated automated test suite.

## Features

- Secure registration and OAuth2-compatible JWT login
- Bcrypt password hashing and active-user checks
- User and administrator authorization
- Complete student CRUD with case-insensitive search
- Complete internship application CRUD and status updates
- Combined application search and filtering
- PostgreSQL production configuration with a SQLite local fallback
- Alembic schema migrations
- Swagger UI and ReDoc documentation
- Isolated in-memory database tests

## Technology stack

- Python 3.11+
- FastAPI and OAuth2 helpers
- SQLAlchemy 2.x
- Pydantic and pydantic-settings
- PostgreSQL with psycopg
- SQLite local fallback and isolated in-memory test database
- Alembic
- Passlib with bcrypt
- PyJWT
- Pytest and HTTPX

## Project structure

```text
app/
|-- core/
|   |-- auth.py
|   `-- security.py
|-- models/
|   |-- internship_application.py
|   |-- student.py
|   `-- user.py
|-- routes/
|   |-- applications.py
|   |-- auth.py
|   `-- students.py
|-- schemas/
|   |-- application.py
|   |-- auth.py
|   |-- student.py
|   `-- system.py
|-- services/
|   |-- application_service.py
|   `-- student_service.py
|-- config.py
|-- database.py
`-- main.py
alembic/
|-- versions/
|   `-- 20260924_0001_initial_schema.py
|-- env.py
`-- script.py.mako
tests/
|-- conftest.py
|-- test_auth.py
|-- test_applications.py
|-- test_config.py
|-- test_main.py
|-- test_models.py
|-- test_search_filtering.py
|-- test_students.py
`-- test_test_database.py
render.yaml
```

## Database entities and relationship

- **User** stores a normalized unique email, bcrypt password hash, role, active state, and creation time. Plain-text passwords are never stored.
- **Student** stores contact and academic details plus timestamps.
- **InternshipApplication** stores internship details, status, dates, optional notes, and timestamps.

One student can have many internship applications. Every application belongs to one student through `internship_applications.student_id`, which references `students.id`.

The initial migration contains the complete schema required by the current backend.

## Environment setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Copy the environment template:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set a strong, random `SECRET_KEY`. Also replace the example `DATABASE_URL` with valid PostgreSQL credentials. SQLite remains the automatic local fallback when `DATABASE_URL` is absent.

### Environment variables

| Variable | Purpose | Example |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy database connection | `postgresql+psycopg://username:password@host:5432/database_name` |
| `SECRET_KEY` | JWT signing key; minimum 32 characters | `replace-with-a-long-random-secret` |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Positive access-token lifetime | `30` |
| `APP_NAME` | OpenAPI application title | `Internship and Student Management API` |
| `DEBUG` | FastAPI debug mode | `false` |

Never commit the populated `.env` file.

## Database migrations

Apply migrations:

```powershell
python -m alembic upgrade head
```

Inspect and validate migration state:

```powershell
python -m alembic current
python -m alembic check
```

## Render deployment

The root `render.yaml` Blueprint defines a free Python web service and a free Render PostgreSQL database. During Blueprint creation, Render injects the database's internal connection string as `DATABASE_URL`, generates `SECRET_KEY`, and sets the remaining non-secret environment variables. No production credentials are stored in this repository.

Render settings:

```text
Build:  pip install -r requirements.txt
Start:  uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health: /health
```

Free Render web services do not support pre-deploy commands. After the Blueprint creates the database, use its external database URL in a trusted local environment and run the migration before using database-backed endpoints:

```powershell
python -m alembic upgrade head
```

Do not commit the external database URL or generated secret. Render PostgreSQL is required for persistent deployment data; the local SQLite fallback is not used when Render supplies `DATABASE_URL`.

## Run locally

```powershell
python -m uvicorn app.main:app --reload
```

Documentation is available at:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Authentication flow

1. Register a normal account with `POST /auth/register`.
2. Submit the registered email in the OAuth2 `username` field and the password to `POST /auth/login`.
3. Use the returned bearer token in the `Authorization` header.
4. In Swagger UI, select **Authorize** and enter the same email and password; Swagger obtains and sends the bearer token automatically.

Public registration always creates the `user` role. Administrator accounts must be provisioned through a trusted internal or manual workflow.

## System endpoints

- `GET /` returns the API name.
- `GET /health` returns `{"status": "healthy"}`.

## Authentication endpoints

- `POST /auth/register` creates a normal `user` account with a bcrypt password hash. Unexpected fields such as `role` are rejected.
- `POST /auth/login` accepts OAuth2 form fields `username` (the user's email) and `password`, then returns a JWT access token.
- `GET /auth/me` returns the active authenticated user's safe profile.
- `GET /auth/admin-check` requires an active user with the `admin` role.

## Student endpoints

- `POST /students` creates a student (admin only).
- `GET /students` lists students and supports optional `search` across name, email, university, and course fields (active authenticated users).
- `GET /students/{student_id}` returns one student (active authenticated users).
- `PUT /students/{student_id}` fully replaces editable student data (admin only).
- `PATCH /students/{student_id}` changes supplied fields only (admin only).
- `DELETE /students/{student_id}` deletes a student (admin only).

Student input validates email format, nonblank text, field lengths, and positive path IDs. Duplicate student emails return `409 Conflict`, missing students return `404 Not Found`, and invalid input returns `422 Unprocessable Content`.

## Internship application endpoints

- `POST /applications` creates an application for an existing student (admin only).
- `GET /applications` lists, searches, and filters applications (active authenticated users).
- `GET /applications/{application_id}` returns one application (active authenticated users).
- `PUT /applications/{application_id}` fully replaces an application (admin only).
- `PATCH /applications/{application_id}` changes supplied fields only (admin only).
- `PATCH /applications/{application_id}/status` changes only `pending`, `accepted`, or `rejected` status (admin only).
- `DELETE /applications/{application_id}` deletes an application (admin only).

Application input validates positive student IDs, valid dates, allowed statuses, and nonblank required text. Every application references an existing student; one student may own many applications. Missing applications or referenced students return `404 Not Found`.

### Application search and filters

`GET /applications` supports these optional query parameters:

- `search` searches company, position, internship type, and location.
- `status` accepts only `pending`, `accepted`, or `rejected`.
- `company_name`, `position`, `internship_type`, and `location` perform case-insensitive partial matching.
- `student_id` requires a positive integer.

Parameters can be combined. No matches return an empty JSON list with `200 OK`.

Examples:

```text
GET /applications?status=pending
GET /applications?location=Accra&status=accepted
GET /applications?search=software&student_id=2
GET /students?search=computer
```

## Error responses

- `401 Unauthorized`: missing, invalid, or expired authentication.
- `403 Forbidden`: inactive accounts or insufficient permissions.
- `404 Not Found`: missing student or application.
- `409 Conflict`: duplicate registered user or student email.
- `422 Unprocessable Content`: invalid IDs, statuses, emails, query parameters, or request bodies.

Database exception details are not exposed through API responses.

## Tests

```powershell
python -m pytest
```

Authentication, CRUD, relationship, search, filtering, and error-handling tests override the application's database dependency with an isolated in-memory SQLite database. They never connect to or modify local or production data.

The fixture recreates the schema before each test and drops it afterward, ensuring reliable isolation and cleanup.

## Security notes

- Never commit `.env`.
- Replace the example `SECRET_KEY` before sharing or deploying an environment.
- JWT tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Public registration cannot create administrators. Admin accounts must be provisioned through a trusted manual or internal workflow.

"""Flask-route-level tests for src.deliver.app's login flow.

Everything else in the dashboard is already covered framework-free in
test_deliver_dashboard.py; this file is specifically for the login route
itself now that it does a real password check (src.security.authentication)
instead of the old picker - the HTTP wiring (form fields, session, redirects)
is worth exercising through an actual Flask test client, not just the
authentication module in isolation.
"""

from __future__ import annotations

import pytest

from src.deliver.app import create_app


@pytest.fixture
def client(seeded_db):
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_student_can_log_in_with_seeded_demo_credentials_and_reach_dashboard(client):
    response = client.post(
        "/login",
        data={"role": "student", "student_number": "DEMO0001", "password": "DEMO0001"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"learning journey" in response.data.lower()


def test_student_login_rejects_wrong_password(client):
    response = client.post(
        "/login",
        data={"role": "student", "student_number": "DEMO0001", "password": "not-the-password"},
    )
    assert response.status_code == 200
    assert b"Incorrect" in response.data
    with client.session_transaction() as recorded_session:
        assert "role" not in recorded_session


def test_staff_can_log_in_with_seeded_demo_credentials(client):
    response = client.post(
        "/login",
        data={"role": "staff", "username": "staff", "password": "staff123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with client.session_transaction() as recorded_session:
        assert recorded_session["role"] == "staff"


def test_dashboard_redirects_to_login_when_not_signed_in(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_without_password_shows_error_not_crash(client):
    response = client.post(
        "/login", data={"role": "student", "student_number": "DEMO0001", "password": ""}
    )
    assert response.status_code == 200
    assert b"Enter your student number and password" in response.data


def test_staff_can_reach_coordinator_report(client):
    client.post("/login", data={"role": "staff", "username": "staff", "password": "staff123"})

    response = client.get("/coordinator")

    assert response.status_code == 200
    assert b"Coordinator report" in response.data


def test_student_is_forbidden_from_coordinator_report(client):
    client.post(
        "/login",
        data={"role": "student", "student_number": "DEMO0001", "password": "DEMO0001"},
    )

    response = client.get("/coordinator")

    assert response.status_code == 403


def test_coordinator_report_redirects_to_login_when_not_signed_in(client):
    response = client.get("/coordinator", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

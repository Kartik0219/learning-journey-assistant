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


def test_staff_and_admin_accounts_no_longer_exist(client):
    """The app is student-only: the old staff/admin demo logins are refused."""
    for username, password in (("staff", "staff123"), ("admin", "admin123")):
        response = client.post(
            "/login", data={"role": "staff", "student_number": username, "password": password}
        )
        assert response.status_code == 200
        assert b"Incorrect" in response.data
        with client.session_transaction() as recorded_session:
            assert "role" not in recorded_session


def test_coordinator_and_review_pages_are_gone(client):
    _log_in_student(client)
    for path in ("/coordinator", "/review"):
        assert client.get(path).status_code == 404


def test_old_staff_session_cookie_is_signed_out_not_an_error(client):
    with client.session_transaction() as recorded_session:
        recorded_session["role"] = "staff"
        recorded_session["student_id"] = None
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


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


def _log_in_student(client, student_number: str = "DEMO0001") -> None:
    client.post(
        "/login",
        data={"role": "student", "student_number": student_number, "password": student_number},
    )


def test_results_redirects_to_login_when_not_signed_in(client):
    response = client.get("/results", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_results_page_shows_every_workbook_column_per_subject(client):
    _log_in_student(client)
    response = client.get("/results")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    for heading in ("Assessment Type", "Score (1-100)", "Feedback Comment", "SILO's", "Weight", "Weighted Score"):
        assert heading in body
    assert "DEMO101" in body  # the sample student's subject


def test_results_page_shows_weight_and_weighted_score_from_the_workbook(client):
    from src.db.database import get_session
    from src.db.models import AssessmentResult, Student

    with get_session() as session:
        student = next(s for s in session.query(Student).all() if s.student_number == "DEMO0001")
        result = session.query(AssessmentResult).filter_by(student_id=student.id).first()
        result.silo_tags_text = "SILO2: Apply demo techniques"
        result.weight = 0.25
        result.weighted_score = 12.75

    _log_in_student(client)
    body = client.get("/results").get_data(as_text=True)

    assert "25%" in body
    assert "12.75" in body
    assert "Apply demo techniques" in body
    assert "Weighted total: 12.75" in body


def test_student_cannot_read_another_students_results(seeded_db):
    """N6: the results data function refuses a student asking for someone else."""
    import pytest

    from src.db.database import get_session
    from src.db.models import Student
    from src.deliver.dashboard_api import get_student_results
    from src.security.authorization import Actor, AuthorizationError, Role

    with get_session() as session:
        students = {s.student_number: s for s in session.query(Student).all()}
        me, other = students["DEMO0001"], students["DEMO0002"]
        with pytest.raises(AuthorizationError):
            get_student_results(session, Actor(role=Role.STUDENT, student_id=me.id), other.id)

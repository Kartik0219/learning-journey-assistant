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


# --- Staff skill-gap review queue routes (F4/F5, N6) ----------------------


def _seed_pending_gap() -> int:
    """One held-back gap on the first seeded result, built directly so the
    route tests don't depend on how the fixture's feedback happens to score
    against the confidence threshold."""
    from src.db.database import get_session
    from src.db.models import AssessmentResult, LearningOutcome, SkillGap

    with get_session() as session:
        result = session.query(AssessmentResult).first()
        lo = (
            session.query(LearningOutcome)
            .filter_by(subject_id=result.assessment.subject_id)
            .first()
        )
        gap = SkillGap(
            assessment_result_id=result.id,
            learning_outcome_id=lo.id,
            source_evidence_text="the trade-off analysis was one-sided",
            severity="medium",
            confidence=0.08,
            reviewed=False,
            review_status="pending",
        )
        session.add(gap)
        session.flush()
        return gap.id


def _log_in(client, role: str) -> None:
    if role == "student":
        client.post(
            "/login",
            data={"role": "student", "student_number": "DEMO0001", "password": "DEMO0001"},
        )
    else:
        client.post("/login", data={"role": role, "username": role, "password": f"{role}123"})


def test_review_queue_redirects_to_login_when_not_signed_in(client):
    assert client.get("/review", follow_redirects=False).status_code == 302


def test_staff_can_open_the_review_queue(client):
    _seed_pending_gap()
    _log_in(client, "staff")
    response = client.get("/review")
    assert response.status_code == 200
    assert b"trade-off analysis was one-sided" in response.data


def test_student_gets_403_on_the_review_queue(client):
    _seed_pending_gap()
    _log_in(client, "student")
    assert client.get("/review").status_code == 403


def test_student_posting_a_decision_directly_gets_403_and_changes_nothing(client):
    """N6 in its real form: the check is on the server, so hiding the nav
    link is not what protects this. A student POSTing straight at the
    endpoint must be refused and must not move the gap."""
    from src.db.database import get_session
    from src.db.models import SkillGap

    gap_id = _seed_pending_gap()
    _log_in(client, "student")

    response = client.post(f"/review/{gap_id}", data={"decision": "approve"})
    assert response.status_code == 403

    with get_session() as session:
        gap = session.get(SkillGap, gap_id)
        assert gap.review_status == "pending"
        assert gap.reviewed is False


def test_staff_approval_through_the_route_publishes_the_gap(client):
    from src.db.database import get_session
    from src.db.models import SkillGap

    gap_id = _seed_pending_gap()
    _log_in(client, "staff")

    response = client.post(f"/review/{gap_id}", data={"decision": "approve"})
    assert response.status_code == 302  # back to the queue

    with get_session() as session:
        gap = session.get(SkillGap, gap_id)
        assert gap.review_status == "approved"
        assert gap.reviewed is True


def test_malformed_decision_is_a_400(client):
    gap_id = _seed_pending_gap()
    _log_in(client, "staff")
    assert client.post(f"/review/{gap_id}", data={"decision": "sure"}).status_code == 400

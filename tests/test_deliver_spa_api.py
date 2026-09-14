"""The JSON API behind the React SPA (src/deliver/spa_api.py).

The important property is that it is not a second, weaker door into the
data: it must enforce exactly the N6 access rule and N2 consent gate the
server-rendered pages do.
"""

from __future__ import annotations

import pytest

from src.db.database import get_session
from src.db.models import ConsentRecord, Student, StudyEngagement, StudyRecommendation
from src.deliver.app import create_app
from src.pipeline import run_estimate_stage, run_model_stage


@pytest.fixture
def client(seeded_db):
    with get_session() as db:
        run_model_stage(db)
    with get_session() as db:
        run_estimate_stage(db)
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _login_student(client, number="DEMO0001"):
    client.post("/login", data={"role": "student", "student_number": number, "password": number})


def _id_of(number):
    with get_session() as db:
        from src.security.encryption import blind_index

        return db.query(Student).filter_by(student_number_hash=blind_index(number)).one().id


def test_every_endpoint_requires_sign_in(client):
    for path in ("/api/session", "/api/students/1/dashboard", "/api/students/1/results",
                 "/api/students/1/resources"):
        response = client.get(path)
        assert response.status_code == 401, path
        assert response.get_json()["error"] == "not_signed_in"


def test_student_session_lists_only_themself(client):
    _login_student(client)
    data = client.get("/api/session").get_json()
    assert data["role"] == "student"
    assert [s["id"] for s in data["students"]] == [_id_of("DEMO0001")]



def test_student_gets_their_own_dashboard_with_real_scores(client):
    _login_student(client)
    sid = _id_of("DEMO0001")
    data = client.get(f"/api/students/{sid}/dashboard").get_json()
    assert data["student"]["id"] == sid
    assert any(o["mastery_pct"] is not None for o in data["outcomes"])


def test_student_cannot_read_another_students_records(client):
    _login_student(client)
    other = _id_of("DEMO0002")
    for kind in ("dashboard", "results", "resources"):
        response = client.get(f"/api/students/{other}/{kind}")
        assert response.status_code == 403, kind


def test_results_group_by_subject_with_silo_codes(client):
    _login_student(client)
    data = client.get(f"/api/students/{_id_of('DEMO0001')}/results").get_json()
    subject = data["subjects"][0]
    assert subject["code"] == "DEMO101"
    assert subject["assessments"]
    assert subject["learning_outcomes"][0]["code"] == "SILO1"
    for row in subject["assessments"]:
        assert all(code.startswith("SILO") for code in row["silo_codes"])


def test_consent_withdrawal_blocks_the_api_too(client):
    sid = _id_of("DEMO0001")
    with get_session() as db:
        import datetime as dt

        consent = db.query(ConsentRecord).filter_by(student_id=sid).one()
        consent.withdrawn_date = dt.datetime.now(dt.UTC)
    _login_student(client)
    response = client.get(f"/api/students/{sid}/dashboard")
    assert response.status_code == 403
    assert response.get_json()["error"] == "no_consent"


def test_practice_records_engagement_for_own_recommendation(client):
    _login_student(client)
    sid = _id_of("DEMO0001")
    with get_session() as db:
        rec_id = db.query(StudyRecommendation).filter_by(student_id=sid).first().id

    response = client.post(f"/api/recommendations/{rec_id}/practice", json={})
    assert response.status_code == 200
    with get_session() as db:
        assert db.query(StudyEngagement).filter_by(study_recommendation_id=rec_id).count() == 1


def test_practice_rejects_non_json_and_other_students(client):
    _login_student(client)
    with get_session() as db:
        recs = db.query(StudyRecommendation)
        other_rec = recs.filter_by(student_id=_id_of("DEMO0002")).first().id
        own_rec = recs.filter_by(student_id=_id_of("DEMO0001")).first().id

    assert client.post(f"/api/recommendations/{own_rec}/practice", data={}).status_code == 415
    assert client.post(f"/api/recommendations/{other_rec}/practice", json={}).status_code == 403


def test_login_next_returns_to_the_spa_but_never_off_site(client):
    response = client.post(
        "/login?next=/app/",
        data={"role": "student", "student_number": "DEMO0001", "password": "DEMO0001"},
    )
    assert response.headers["Location"].endswith("/app/")

    client.get("/logout")
    response = client.post(
        "/login?next=https://evil.example/",
        data={"role": "student", "student_number": "DEMO0001", "password": "DEMO0001"},
    )
    assert "evil.example" not in response.headers["Location"]


def test_login_without_next_lands_in_the_student_app(client):
    """The React student app is the main app once its bundle is built."""
    response = client.post("/login", data={"student_number": "DEMO0001", "password": "DEMO0001"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/app/")
    assert client.get("/", follow_redirects=False).headers["Location"].endswith("/app/")


def test_ai_insight_endpoint_is_off_without_a_provider_and_guards_access(client):
    assert client.get("/api/students/1/ai-insight").status_code == 401

    _login_student(client)
    own = client.get(f"/api/students/{_id_of('DEMO0001')}/ai-insight")
    assert own.status_code == 200
    assert own.get_json()["enabled"] is False

    other = client.get(f"/api/students/{_id_of('DEMO0002')}/ai-insight")
    assert other.status_code == 403

"""The written insight is arithmetic on the student's own marks: it must be
deterministic, gated like everything else, and never claim more than the
numbers support."""

from __future__ import annotations

import pytest

from src.db.database import get_session
from src.db.models import Student
from src.deliver.app import create_app
from src.deliver.insight_api import band_for, next_band_for
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


def _login(client, number="DEMO0001"):
    client.post("/login", data={"student_number": number, "password": number})


def _id_of(number):
    with get_session() as db:
        from src.security.encryption import blind_index

        return db.query(Student).filter_by(student_number_hash=blind_index(number)).one().id


def test_bands_follow_la_trobe_thresholds():
    assert band_for(80)[0] == "High Distinction"
    assert band_for(79.99)[0] == "Distinction"
    assert band_for(60)[0] == "Credit"
    assert band_for(50)[0] == "Pass"
    assert band_for(49.9)[0] == "Fail"
    assert next_band_for(50.65) == ("Credit", 9.35)
    assert next_band_for(85) is None


def test_insight_requires_sign_in_and_is_own_record_only(client):
    assert client.get("/api/students/1/insight").status_code == 401
    _login(client)
    assert client.get(f"/api/students/{_id_of('DEMO0002')}/insight").status_code == 403


def test_insight_is_written_from_the_students_numbers_and_is_deterministic(client):
    _login(client)
    sid = _id_of("DEMO0001")
    first = client.get(f"/api/students/{sid}/insight").get_json()
    second = client.get(f"/api/students/{sid}/insight").get_json()
    assert first == second, "same marks must produce the same words"

    assert first["method"] == "deterministic"
    assert first["generated_from"]["assessments"] > 0
    assert first["headline"]
    assert isinstance(first["this_week"], list) and first["this_week"]

    for subject in first["subjects"]:
        assert subject["paragraphs"], subject["code"]
        assert subject["band"] in {"High Distinction", "Distinction", "Credit", "Pass", "Fail", "No results yet"}
        # every subject total quoted in the prose is the one the API reports
        if subject["total"] is not None:
            assert any(str(int(subject["total"])) in p or f"{subject['total']:.2f}".rstrip("0").rstrip(".") in p
                       for p in subject["paragraphs"])
        for outcome in subject["weakest_outcomes"]:
            assert outcome["code"] in subject["paragraphs"][1] if len(subject["paragraphs"]) > 1 else True

    # the sample dataset has no weights, so there is no "biggest lever" to claim
    assert all(s["biggest_lever"] is None for s in first["subjects"] if not s["weighted"])


def test_old_ai_route_still_exists_for_bookmarks(client):
    _login(client)
    body = client.get(f"/api/students/{_id_of('DEMO0001')}/ai-insight").get_json()
    assert body["enabled"] is False

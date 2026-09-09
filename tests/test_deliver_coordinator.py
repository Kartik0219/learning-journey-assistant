"""Tests for the app-build phase database feature: the Staff/Admin-only
cohort-level coordinator report (src.deliver.coordinator_api).
"""

from __future__ import annotations

import pytest

from src.db.database import get_session
from src.db.models import AssessmentResult, LearningOutcome, Student
from src.deliver.coordinator_api import AT_RISK_MASTERY_THRESHOLD, get_coordinator_report
from src.estimate.mastery import calculate_mastery_score, generate_study_material
from src.model.silo_mapping import extract_skill_gaps, map_gap_to_learning_outcome
from src.security.authorization import Actor, AuthorizationError, Role
from src.security.consent import record_consent


def _student(session, student_number: str) -> Student:
    return next(
        s for s in session.query(Student).all() if s.student_number == student_number
    )


def _run_model_and_estimate_for_all(session) -> None:
    for student in session.query(Student).all():
        for result in session.query(AssessmentResult).filter_by(student_id=student.id).all():
            for gap in extract_skill_gaps(session, result):
                map_gap_to_learning_outcome(session, gap)
        for lo in session.query(LearningOutcome).all():
            calculate_mastery_score(session, student, lo)
            generate_study_material(session, student, lo)


def test_student_actor_is_denied(seeded_db):
    with get_session() as session:
        student = _student(session, "DEMO0001")
        with pytest.raises(AuthorizationError):
            get_coordinator_report(session, Actor(role=Role.STUDENT, student_id=student.id))


def test_staff_actor_sees_cohort_aggregate(seeded_db):
    with get_session() as session:
        _run_model_and_estimate_for_all(session)

        report = get_coordinator_report(session, Actor(role=Role.STAFF))

        assert report["consented_student_count"] == 3
        assert len(report["subjects"]) == 1
        subject = report["subjects"][0]
        assert len(subject["outcomes"]) == 3
        silo2 = next(o for o in subject["outcomes"] if o["code"] == "SILO2")
        assert silo2["student_count"] == 3
        assert silo2["average_mastery_pct"] is not None
        assert silo2["gap_counts"]["low"] >= 1


def test_admin_actor_also_allowed(seeded_db):
    with get_session() as session:
        _run_model_and_estimate_for_all(session)
        report = get_coordinator_report(session, Actor(role=Role.ADMIN))
        assert report["consented_student_count"] == 3


def test_student_without_active_consent_is_excluded_from_every_aggregate(seeded_db):
    with get_session() as session:
        _run_model_and_estimate_for_all(session)

        withdrawn_student = _student(session, "DEMO0002")
        record_consent(session, withdrawn_student, given=False)

        report = get_coordinator_report(session, Actor(role=Role.STAFF))

        assert report["consented_student_count"] == 2
        subject = report["subjects"][0]
        for outcome in subject["outcomes"]:
            assert outcome["student_count"] <= 2
        assert all(s["id"] != withdrawn_student.id for s in report["at_risk_students"])


def test_at_risk_students_listed_below_threshold_and_sorted_ascending(seeded_db):
    with get_session() as session:
        _run_model_and_estimate_for_all(session)

        report = get_coordinator_report(session, Actor(role=Role.STAFF))

        for student in report["at_risk_students"]:
            assert student["average_mastery_pct"] < AT_RISK_MASTERY_THRESHOLD * 100
        percentages = [s["average_mastery_pct"] for s in report["at_risk_students"]]
        assert percentages == sorted(percentages)


def test_report_before_estimate_stage_has_no_averages_but_does_not_crash(seeded_db):
    with get_session() as session:
        report = get_coordinator_report(session, Actor(role=Role.STAFF))

        assert report["consented_student_count"] == 3
        for subject in report["subjects"]:
            for outcome in subject["outcomes"]:
                assert outcome["average_mastery_pct"] is None
                assert outcome["student_count"] == 0
        assert report["at_risk_students"] == []

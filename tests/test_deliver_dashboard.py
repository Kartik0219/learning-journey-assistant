"""Tests for Phase 4 (IOG-40): src.deliver.dashboard_api.get_student_dashboard.

The cross-student-blocking path (require_student_access firing before any
row is read) is already covered in test_security.py, alongside IOG-42's
other authorization tests - this file is the happy-path complement: once
authorization and consent both pass, does the assembled dashboard data
actually look right, and does F4's "never show an unreviewed gap to the
student" hold even when a low-confidence gap exists in the database.
"""

from __future__ import annotations

from src.db.database import get_session
from src.db.models import AssessmentResult, LearningOutcome, SkillGap, Student
from src.deliver.dashboard_api import get_student_dashboard
from src.estimate.mastery import calculate_mastery_score, generate_study_material
from src.model.silo_mapping import extract_skill_gaps, map_gap_to_learning_outcome
from src.security.authorization import Actor, Role


def _student(session, student_number: str) -> Student:
    return next(
        s for s in session.query(Student).all() if s.student_number == student_number
    )


def _run_model_and_estimate_stages(session, student: Student) -> None:
    for result in session.query(AssessmentResult).filter_by(student_id=student.id).all():
        for gap in extract_skill_gaps(session, result):
            map_gap_to_learning_outcome(session, gap)
    for lo in session.query(LearningOutcome).all():
        calculate_mastery_score(session, student, lo)
        generate_study_material(session, student, lo)


def test_dashboard_assembles_mastery_gaps_and_recommendation_for_self_access(seeded_db):
    """DEMO0001 viewing their own dashboard should see all three SILOs,
    with SILO2 carrying its mastery score, its one reviewed gap, and a
    grounded recommendation - and nothing raised, since actor is self."""
    with get_session() as session:
        student = _student(session, "DEMO0001")
        _run_model_and_estimate_stages(session, student)

        data = get_student_dashboard(
            session, Actor(role=Role.STUDENT, student_id=student.id), student_id=student.id
        )

        assert data["student"]["id"] == student.id
        assert data["student"]["display_name"] == "Sample Student A"
        assert len(data["outcomes"]) == 3

        silo2 = next(o for o in data["outcomes"] if o["code"] == "SILO2")
        assert silo2["mastery_pct"] is not None
        assert silo2["mastery_score"] < 0.72
        assert len(silo2["gaps"]) == 1
        assert silo2["gaps"][0]["evidence"] == "the applied technique had a minor error in step 2"
        assert silo2["gaps"][0]["severity"] == "low"
        assert silo2["recommendation"] is not None
        assert silo2["recommendation"]["method"] == "retrieval_practice"
        assert silo2["recommendation"]["source_title"] is not None

        silo1 = next(o for o in data["outcomes"] if o["code"] == "SILO1")
        assert silo1["gaps"] == []


def test_dashboard_priority_outcomes_are_the_three_lowest_scoring(seeded_db):
    """DEMO0002 has all three SILOs scored (two reduced by gaps, one
    not) - priority_outcomes should list all three (only 3 exist here),
    sorted ascending by mastery score."""
    with get_session() as session:
        student = _student(session, "DEMO0002")
        _run_model_and_estimate_stages(session, student)

        data = get_student_dashboard(
            session, Actor(role=Role.STAFF), student_id=student.id
        )

        scores = [o["mastery_score"] for o in data["priority_outcomes"]]
        assert scores == sorted(scores)
        assert len(data["priority_outcomes"]) == 3
        # SILO1 (0.535, gap confidence 0.30) edges out SILO3 (0.5495, gap
        # confidence 0.20) for lowest, since medium severity weighs both
        # gaps equally and SILO1's gap has the higher confidence.
        assert data["priority_outcomes"][0]["code"] == "SILO1"


def test_dashboard_never_surfaces_an_unreviewed_gap(seeded_db):
    """F4: 'items with low confidence are held for review and are not
    shown to the student until checked.' Insert a gap with reviewed=False
    directly (bypassing whatever confidence the real extractor would
    have assigned it) and confirm the dashboard hides it regardless of
    everything else being otherwise identical to a shown gap."""
    with get_session() as session:
        student = _student(session, "DEMO0001")
        result = session.query(AssessmentResult).filter_by(student_id=student.id).one()
        silo1 = session.query(LearningOutcome).filter_by(code="SILO1").one()

        hidden_gap = SkillGap(
            assessment_result_id=result.id,
            learning_outcome_id=silo1.id,
            source_evidence_text="a clause that scored below the confidence threshold",
            severity="medium",
            confidence=0.01,
            reviewed=False,
        )
        session.add(hidden_gap)
        calculate_mastery_score(session, student, silo1)
        session.flush()

        data = get_student_dashboard(
            session, Actor(role=Role.STUDENT, student_id=student.id), student_id=student.id
        )

        silo1_data = next(o for o in data["outcomes"] if o["code"] == "SILO1")
        assert silo1_data["gaps"] == []
        # The unreviewed gap must not have affected the score either -
        # calculate_mastery_score's own _gaps_for filters on reviewed too.
        assert silo1_data["mastery_score"] == 0.72


def test_dashboard_subjects_overview_averages_mastery_within_each_subject(seeded_db):
    """App-build phase frontend feature: data['subjects'] rolls up each
    outcome's mastery into a per-subject average. The sample dataset has
    only one subject, so this should be a single entry averaging all
    three SILO scores."""
    with get_session() as session:
        student = _student(session, "DEMO0002")
        _run_model_and_estimate_stages(session, student)

        data = get_student_dashboard(
            session, Actor(role=Role.STUDENT, student_id=student.id), student_id=student.id
        )

        assert len(data["subjects"]) == 1
        outcome_scores = [o["mastery_score"] for o in data["outcomes"]]
        expected_pct = round(sum(outcome_scores) / len(outcome_scores) * 100)
        assert data["subjects"][0]["average_mastery_pct"] == expected_pct


def test_dashboard_subjects_overview_empty_before_estimate_stage(seeded_db):
    with get_session() as session:
        student = _student(session, "DEMO0003")

        data = get_student_dashboard(
            session, Actor(role=Role.STUDENT, student_id=student.id), student_id=student.id
        )

        assert data["subjects"] == []


def test_dashboard_before_estimate_stage_has_no_mastery_or_recommendation(seeded_db):
    """A student with rows in the DB but before the Estimate stage has
    run should get a dashboard that renders (no crash), just with
    mastery/recommendation left None rather than fabricated."""
    with get_session() as session:
        student = _student(session, "DEMO0003")

        data = get_student_dashboard(
            session, Actor(role=Role.STUDENT, student_id=student.id), student_id=student.id
        )

        assert len(data["outcomes"]) == 3
        for outcome in data["outcomes"]:
            assert outcome["mastery_score"] is None
            assert outcome["mastery_pct"] is None
            assert outcome["recommendation"] is None
        assert data["priority_outcomes"] == []

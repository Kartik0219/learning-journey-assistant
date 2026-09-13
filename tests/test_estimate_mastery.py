"""Tests for Phase 4 (IOG-38 continued, IOG-39): weighted mastery scoring,
fixed-table study-method selection, grounded study-material generation,
and the engagement feedback loop (src.estimate.mastery).

Built on the same bundled sample dataset as test_model_silo_mapping.py,
run through the Model stage first so the gaps these scores weight
against actually exist - these two phases are not independently
testable in a way that reflects real behaviour, since F6 explicitly
depends on F3/F5's output.
"""

from __future__ import annotations

from src.db.database import get_session
from src.db.models import AssessmentResult, LearningOutcome, MasteryScore, Student
from src.estimate.mastery import (
    STUDY_METHOD_TABLE,
    calculate_mastery_score,
    generate_study_material,
    recommend_study_method,
    record_engagement,
)
from src.model.silo_mapping import extract_skill_gaps, map_gap_to_learning_outcome


def _student(session, student_number: str) -> Student:
    return next(
        s for s in session.query(Student).all() if s.student_number == student_number
    )


def _run_model_stage(session) -> None:
    for result in session.query(AssessmentResult).all():
        for gap in extract_skill_gaps(session, result):
            map_gap_to_learning_outcome(session, gap)


def test_mastery_score_with_no_gaps_equals_assessment_baseline(seeded_db):
    """DEMO0003 (score 91, positive feedback) has no gaps on any SILO -
    mastery should equal the raw assessment score with no penalty."""
    with get_session() as session:
        _run_model_stage(session)
        student = _student(session, "DEMO0003")
        for lo in session.query(LearningOutcome).all():
            mastery = calculate_mastery_score(session, student, lo)
            assert mastery.score == 0.91
            assert "No reviewed skill gaps" in mastery.explanation_text
            assert "91%" in mastery.explanation_text


def test_mastery_score_is_reduced_by_a_reviewed_gap_and_explanation_names_it(seeded_db):
    """DEMO0001's SILO2 mastery should be reduced from the 72% baseline
    by severity_weight['low'] * confidence for the one mapped gap, and
    the explanation text must name the exact evidence quote (F6:
    "explainable from the evidence")."""
    with get_session() as session:
        _run_model_stage(session)
        student = _student(session, "DEMO0001")
        silo2 = session.query(LearningOutcome).filter_by(code="SILO2").one()

        mastery = calculate_mastery_score(session, student, silo2)

        assert mastery.score < 0.72  # penalised below the raw baseline
        assert mastery.score > 0.0
        assert "the applied technique had a minor error in step 2" in mastery.explanation_text
        assert "low severity" in mastery.explanation_text

        # SILO1/SILO3 for the same student have no gaps mapped to them -
        # only the outcome the gap actually maps to should be affected.
        silo1 = session.query(LearningOutcome).filter_by(code="SILO1").one()
        mastery1 = calculate_mastery_score(session, student, silo1)
        assert mastery1.score == 0.72


def test_mastery_score_is_clipped_to_zero_and_one(seeded_db):
    """calculate_mastery_score's formula clips explicitly - verify the
    clip actually bites rather than trusting the arithmetic never
    over/undershoots. A student with no assessment results at all should
    floor at 0.0, never go negative."""
    with get_session() as session:
        student = _student(session, "DEMO0001")
        lo = session.query(LearningOutcome).filter_by(code="SILO1").one()

        # Detach this student's only result from this subject to simulate
        # "no relevant results yet" without deleting rows other tests rely on.
        result = session.query(AssessmentResult).filter_by(student_id=student.id).one()
        result.score = None
        session.flush()

        mastery = calculate_mastery_score(session, student, lo)
        assert mastery.score == 0.0


# --- Real-dataset path (IOG-33): results carry explicit SILO tags ---
#
# Reuses the sample DEMO subject (SILO1-3) with silo_tags_text set by hand,
# the same approach as test_model_silo_mapping.py - the real xlsx is
# gitignored and never available to the test suite.


def _tag_result(session, student: Student, silo_tags_text: str, score: float) -> AssessmentResult:
    result = session.query(AssessmentResult).filter_by(student_id=student.id).first()
    result.silo_tags_text = silo_tags_text
    result.score = score
    session.flush()
    return result


def _add_tagged_result(session, student: Student, silo_tags_text: str, score: float) -> AssessmentResult:
    """A second result in the same subject - the real dataset has 11
    assessments per subject, the sample dataset only one."""
    existing = session.query(AssessmentResult).filter_by(student_id=student.id).first()
    result = AssessmentResult(
        assessment_id=existing.assessment_id,
        student_id=student.id,
        score=score,
        silo_tags_text=silo_tags_text,
    )
    session.add(result)
    session.flush()
    return result


def test_tagged_gap_is_not_penalised_twice(seeded_db):
    """A 51% result tagged SILO2 already sets SILO2's baseline to 51%. Its
    gap's severity comes from that same score, so subtracting it again
    drove real students at ~50% to 0% mastery. The gap must still appear
    in the explanation as evidence."""
    with get_session() as session:
        student = _student(session, "DEMO0001")
        _tag_result(session, student, "SILO2: Apply demo techniques", score=51.0)
        _run_model_stage(session)
        silo2 = session.query(LearningOutcome).filter_by(code="SILO2").one()

        mastery = calculate_mastery_score(session, student, silo2)

        assert mastery.score == 0.51
        assert "SILO2: Apply demo techniques" in mastery.explanation_text
        assert "already reflected in the baseline" in mastery.explanation_text


def test_tagged_baseline_uses_only_results_tagged_with_that_outcome(seeded_db):
    with get_session() as session:
        student = _student(session, "DEMO0001")
        _tag_result(session, student, "SILO2: Apply demo techniques", score=51.0)
        _add_tagged_result(session, student, "SILO1: Explain core concepts", score=90.0)
        _run_model_stage(session)
        outcomes = {lo.code: lo for lo in session.query(LearningOutcome).all()}

        assert calculate_mastery_score(session, student, outcomes["SILO2"]).score == 0.51
        silo1 = calculate_mastery_score(session, student, outcomes["SILO1"])
        assert silo1.score == 0.90
        assert "tagged with SILO1" in silo1.explanation_text


def test_tagged_baseline_is_weighted_by_assessment_weight(seeded_db):
    """Real workbook: a 54 on a 15% test and a 50 on a 40% exam give
    (54*0.15 + 50*0.40) / 0.55 = 51.09%, not the plain mean of 52%."""
    with get_session() as session:
        student = _student(session, "DEMO0001")
        test = _tag_result(session, student, "SILO2: Apply demo techniques", score=54.0)
        test.weight = 0.15
        exam = _add_tagged_result(session, student, "SILO2: Apply demo techniques", score=50.0)
        exam.weight = 0.40
        session.flush()
        _run_model_stage(session)
        silo2 = session.query(LearningOutcome).filter_by(code="SILO2").one()

        mastery = calculate_mastery_score(session, student, silo2)

        assert mastery.score == round((54 * 0.15 + 50 * 0.40) / 0.55 / 100, 4)
        assert "weighted by each assessment's weight" in mastery.explanation_text


def test_outcome_with_no_tagged_results_falls_back_to_the_subject_average(seeded_db):
    with get_session() as session:
        student = _student(session, "DEMO0001")
        _tag_result(session, student, "SILO2: Apply demo techniques", score=51.0)
        _add_tagged_result(session, student, "SILO1: Explain core concepts", score=90.0)
        _run_model_stage(session)
        silo3 = session.query(LearningOutcome).filter_by(code="SILO3").one()

        mastery = calculate_mastery_score(session, student, silo3)

        assert mastery.score == 0.705
        assert "in this subject" in mastery.explanation_text


def test_recommend_study_method_follows_the_fixed_table(seeded_db):
    """F7: no model chooses this - it's a pure lookup keyed by the
    outcome's gap type, and every entry in STUDY_METHOD_TABLE should be
    reachable from the sample data's three SILOs."""
    with get_session() as session:
        outcomes = {lo.code: lo for lo in session.query(LearningOutcome).all()}

        assert recommend_study_method(outcomes["SILO1"]) == STUDY_METHOD_TABLE["conceptual"]
        assert recommend_study_method(outcomes["SILO2"]) == STUDY_METHOD_TABLE["application"]
        assert recommend_study_method(outcomes["SILO3"]) == STUDY_METHOD_TABLE["evaluation"]

        assert recommend_study_method(outcomes["SILO1"]) == "worked_example"
        assert recommend_study_method(outcomes["SILO2"]) == "retrieval_practice"
        assert recommend_study_method(outcomes["SILO3"]) == "spaced_practice"


def test_generate_study_material_is_grounded_in_a_real_topic_material(seeded_db):
    """F8/F9: the generated text must be built from - and cite - an
    actual TopicMaterial row, never freely generated prose."""
    with get_session() as session:
        student = _student(session, "DEMO0002")
        silo1 = session.query(LearningOutcome).filter_by(code="SILO1").one()

        recommendation = generate_study_material(session, student, silo1)

        assert recommendation.source_topic_material_id is not None
        source = recommendation.source_topic_material
        assert source.subject_id == silo1.subject_id
        # The recommendation text must actually contain the source
        # passage verbatim - "grounded", not paraphrased.
        assert source.passage_text in recommendation.material_text
        assert source.title in recommendation.material_text
        assert recommendation.method == "worked_example"


def test_generate_study_material_with_no_topic_materials_flags_instead_of_fabricating(
    seeded_db,
):
    """If a subject has zero topic materials, F8/F9 must not invent
    content - it should say so plainly instead."""
    with get_session() as session:
        from src.db.models import Subject, TopicMaterial

        student = _student(session, "DEMO0001")
        silo1 = session.query(LearningOutcome).filter_by(code="SILO1").one()

        # Remove this subject's topic materials for this one test.
        subject = session.get(Subject, silo1.subject_id)
        for material in list(session.query(TopicMaterial).filter_by(subject_id=subject.id)):
            session.delete(material)
        session.flush()

        recommendation = generate_study_material(session, student, silo1)

        assert recommendation.source_topic_material_id is None
        assert "No topic material is available" in recommendation.material_text


def test_record_engagement_recalculates_mastery_with_a_capped_bonus(seeded_db):
    """F11: completing a study recommendation should immediately nudge
    the affected MasteryScore up by ENGAGEMENT_BONUS_PER_COMPLETION,
    reflected in both the score and the explanation text - not just
    logged and left for the next pipeline run."""
    with get_session() as session:
        _run_model_stage(session)
        student = _student(session, "DEMO0002")
        silo1 = session.query(LearningOutcome).filter_by(code="SILO1").one()

        before = calculate_mastery_score(session, student, silo1)
        score_before = before.score
        assert score_before == 0.535

        recommendation = generate_study_material(session, student, silo1)
        record_engagement(session, student, recommendation, completed=True)

        after = (
            session.query(MasteryScore)
            .filter_by(student_id=student.id, learning_outcome_id=silo1.id)
            .one()
        )
        assert after.score == round(score_before + 0.05, 4)
        assert "completed study practice" in after.explanation_text


def test_record_engagement_bonus_is_capped(seeded_db):
    """Repeated completions of the same recommendation shouldn't be able
    to inflate mastery past ENGAGEMENT_BONUS_CAP above the base score."""
    with get_session() as session:
        _run_model_stage(session)
        student = _student(session, "DEMO0003")
        silo1 = session.query(LearningOutcome).filter_by(code="SILO1").one()
        recommendation = generate_study_material(session, student, silo1)

        for _ in range(10):
            record_engagement(session, student, recommendation, completed=True)

        final = calculate_mastery_score(session, student, silo1)
        # Baseline 0.91 + capped bonus 0.15, clipped to 1.0.
        assert final.score == 1.0

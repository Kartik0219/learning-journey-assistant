"""Tests for the app-build phase AI feature: TF-IDF-grounded practice-quiz
generation (src.estimate.quiz), the F8 gap docs/ENVIRONMENT_SETUP.md had
flagged as "not yet built".
"""

from __future__ import annotations

from src.db.database import get_session
from src.db.models import AssessmentResult, LearningOutcome, Student
from src.estimate.quiz import generate_quiz_questions, latest_quiz_questions
from src.model.silo_mapping import extract_skill_gaps, map_gap_to_learning_outcome


def _student(session, student_number: str) -> Student:
    return next(
        s for s in session.query(Student).all() if s.student_number == student_number
    )


def _run_model_stage(session, student: Student) -> None:
    for result in session.query(AssessmentResult).filter_by(student_id=student.id).all():
        for gap in extract_skill_gaps(session, result):
            map_gap_to_learning_outcome(session, gap)


def test_generate_quiz_questions_produces_one_per_reviewed_gap(seeded_db):
    """DEMO0001 has exactly one reviewed gap, mapped to SILO2 - that
    should yield exactly one grounded question for SILO2, none for the
    other SILOs."""
    with get_session() as session:
        student = _student(session, "DEMO0001")
        _run_model_stage(session, student)

        silo2 = session.query(LearningOutcome).filter_by(code="SILO2").one()
        questions = generate_quiz_questions(session, student, silo2)

        assert len(questions) == 1
        question = questions[0]
        assert question.question_type == "apply"  # SILO2 is "Apply..." -> application gap type
        assert "the applied technique had a minor error in step 2" in question.question_text
        assert question.source_skill_gap_id is not None


def test_generate_quiz_questions_is_empty_when_no_reviewed_gaps(seeded_db):
    """DEMO0003's feedback is entirely positive - no gaps, so no quiz
    questions either. A mastered outcome shouldn't manufacture busywork."""
    with get_session() as session:
        student = _student(session, "DEMO0003")
        _run_model_stage(session, student)

        silo1 = session.query(LearningOutcome).filter_by(code="SILO1").one()
        questions = generate_quiz_questions(session, student, silo1)

        assert questions == []


def test_generate_quiz_questions_respects_max_questions(seeded_db):
    """DEMO0002 has two reviewed gaps split across SILO1 and SILO3 - each
    outcome only has one gap mapped to it here, so max_questions=1 should
    still yield exactly one question per outcome without raising."""
    with get_session() as session:
        student = _student(session, "DEMO0002")
        _run_model_stage(session, student)

        silo1 = session.query(LearningOutcome).filter_by(code="SILO1").one()
        questions = generate_quiz_questions(session, student, silo1, max_questions=1)

        assert len(questions) == 1


def test_question_cites_grounded_material_when_available(seeded_db):
    """The sample dataset's topic materials should make at least one
    generated question cite a source passage by title rather than falling
    back to the "no topic material" disclosure."""
    with get_session() as session:
        student = _student(session, "DEMO0001")
        _run_model_stage(session, student)
        silo2 = session.query(LearningOutcome).filter_by(code="SILO2").one()

        questions = generate_quiz_questions(session, student, silo2)

        assert questions[0].source_topic_material_id is not None
        assert "no topic material is available" not in questions[0].question_text.lower()


def test_latest_quiz_questions_reads_back_what_was_generated(seeded_db):
    with get_session() as session:
        student = _student(session, "DEMO0001")
        _run_model_stage(session, student)
        silo2 = session.query(LearningOutcome).filter_by(code="SILO2").one()
        generate_quiz_questions(session, student, silo2)

    with get_session() as session:
        student = _student(session, "DEMO0001")
        silo2 = session.query(LearningOutcome).filter_by(code="SILO2").one()
        questions = latest_quiz_questions(session, student.id, silo2.id)

        assert len(questions) == 1
        assert questions[0].question_type == "apply"


def test_latest_quiz_questions_empty_for_outcome_with_none_generated(seeded_db):
    with get_session() as session:
        student = _student(session, "DEMO0001")
        silo1 = session.query(LearningOutcome).filter_by(code="SILO1").one()

        assert latest_quiz_questions(session, student.id, silo1.id) == []

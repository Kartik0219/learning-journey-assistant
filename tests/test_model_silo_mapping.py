"""Tests for Phase 3 (IOG-37/38): AI-based skill-gap extraction and SILO
mapping (src.model.silo_mapping), checked against the bundled sample
dataset's known feedback text rather than synthetic fixtures - these
three students' feedback was chosen (see data/sample/assessment_results_
sample.csv) specifically to cover "one low-severity gap", "two gaps",
and "zero gaps" in a single small dataset.
"""

from __future__ import annotations

from src.db.database import get_session
from src.db.models import AssessmentResult, LearningOutcome, Student
from src.model.silo_mapping import (
    CONFIDENCE_REVIEW_THRESHOLD,
    extract_skill_gaps,
    gap_type_for,
    map_gap_to_learning_outcome,
)


def _result_for(session, student_number: str) -> AssessmentResult:
    # student_number is encrypted at rest (EncryptedString) so it can't be
    # filtered on directly - decrypt-compare in Python instead, same as
    # any other application code reading this column (see src/db/models.py).
    student = next(
        s for s in session.query(Student).all() if s.student_number == student_number
    )
    return session.query(AssessmentResult).filter_by(student_id=student.id).one()


def test_positive_feedback_yields_zero_gaps(seeded_db):
    """DEMO0003's feedback ('Excellent application and a thoughtful
    discussion of trade-offs.') has no deficiency markers in either
    clause - F3 should not manufacture a gap out of positive feedback."""
    with get_session() as session:
        result = _result_for(session, "DEMO0003")
        gaps = extract_skill_gaps(session, result)
        assert gaps == []


def test_single_deficiency_clause_yields_one_low_severity_gap_mapped_to_silo2(seeded_db):
    """DEMO0001's feedback has one positive clause and one clause
    containing 'minor error', split on the connective 'but'. Only the
    deficiency clause should become a gap, cited verbatim, and it should
    map to SILO2 ('Apply demo techniques...') since the evidence talks
    about applying a technique."""
    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        gaps = extract_skill_gaps(session, result)

        assert len(gaps) == 1
        gap = gaps[0]
        assert gap.source_evidence_text == "the applied technique had a minor error in step 2"
        assert gap.severity == "low"
        assert gap.confidence >= CONFIDENCE_REVIEW_THRESHOLD
        assert gap.reviewed is True

        outcome = map_gap_to_learning_outcome(session, gap)
        assert outcome is not None
        assert outcome.code == "SILO2"
        assert gap.learning_outcome_id == outcome.id
        assert gap.gap_type == "application"


def test_two_deficiency_clauses_yield_two_gaps_mapped_to_silo1_and_silo3(seeded_db):
    """DEMO0002's feedback ('Core concepts were vague and no trade-offs
    were discussed.') has two deficiency clauses split on 'and', neither
    matching a low/high severity marker - both should come back medium
    severity and map to different SILOs."""
    with get_session() as session:
        result = _result_for(session, "DEMO0002")
        gaps = extract_skill_gaps(session, result)

        assert len(gaps) == 2
        by_evidence = {g.source_evidence_text: g for g in gaps}
        assert set(by_evidence) == {
            "Core concepts were vague",
            "no trade-offs were discussed",
        }
        assert all(g.severity == "medium" for g in gaps)
        assert all(g.reviewed for g in gaps)

        mapped = {
            g.source_evidence_text: map_gap_to_learning_outcome(session, g).code
            for g in gaps
        }
        assert mapped["Core concepts were vague"] == "SILO1"
        assert mapped["no trade-offs were discussed"] == "SILO3"


def test_assessment_result_with_no_feedback_text_yields_no_gaps(seeded_db):
    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        result.feedback_text = None
        session.flush()
        assert extract_skill_gaps(session, result) == []


def test_gap_type_for_follows_the_learning_outcome_verb(seeded_db):
    """F7's fixed table (src.estimate.mastery.STUDY_METHOD_TABLE) is
    keyed off this classification - it must stay deterministic and
    match the sample LOs' actual wording."""
    with get_session() as session:
        outcomes = {lo.code: lo for lo in session.query(LearningOutcome).all()}
        assert gap_type_for(outcomes["SILO1"].description) == "conceptual"  # "Explain..."
        assert gap_type_for(outcomes["SILO2"].description) == "application"  # "Apply..."
        # "Critically evaluate..."
        assert gap_type_for(outcomes["SILO3"].description) == "evaluation"


def test_best_similarity_on_empty_corpus_returns_no_match():
    from src.model.silo_mapping import best_similarity

    assert best_similarity("anything", []) == (-1, 0.0)

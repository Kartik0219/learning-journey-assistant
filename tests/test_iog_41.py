"""IOG-41: unit tests for extraction, SILO mapping, and mastery scoring.

The extractor, mapper and scorer already have happy-path coverage in
test_model_silo_mapping.py and test_estimate_mastery.py. This module pins
the contracts those files still leave thin: low-confidence gaps are held,
weak SILO links stay unmapped, unreviewed gaps do not change mastery, the
mastery formula is the documented weighted sum, local extraction still
runs when no LLM is configured, and a real workbook row (when present)
extracts and maps on explicit SILO tags.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.db.database import get_session
from src.db.models import (
    Assessment,
    AssessmentResult,
    LearningOutcome,
    SkillGap,
    Student,
    Subject,
)
from src.estimate.mastery import SEVERITY_WEIGHT, calculate_mastery_score
from src.model.ai_analysis import is_ai_enabled
from src.model.silo_mapping import (
    CONFIDENCE_REVIEW_THRESHOLD,
    LO_MAPPING_THRESHOLD,
    extract_skill_gaps,
    map_gap_to_learning_outcome,
)

WORKBOOK = Path("data/dataset/CSE_results_150_students_3_Subjects.xlsx")


def _student(session, student_number: str) -> Student:
    return next(s for s in session.query(Student).all() if s.student_number == student_number)


def _result_for(session, student_number: str) -> AssessmentResult:
    student = _student(session, student_number)
    return session.query(AssessmentResult).filter_by(student_id=student.id).one()


def test_local_extraction_runs_when_no_llm_is_configured(seeded_db):
    """IOG-41 / IOG-37: credentials unset (conftest) must keep the TF-IDF path."""
    assert is_ai_enabled() is False
    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        gaps = extract_skill_gaps(session, result)
        assert len(gaps) == 1
        assert gaps[0].source_evidence_text == (
            "the applied technique had a minor error in step 2"
        )


def test_tfidf_gap_below_confidence_threshold_is_held(seeded_db, monkeypatch):
    """F4: a low-confidence extraction is stored but not shown or scored."""
    monkeypatch.setattr(
        "src.model.silo_mapping.best_similarity",
        lambda candidate, corpus: (0, CONFIDENCE_REVIEW_THRESHOLD - 0.05),
    )
    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        gaps = extract_skill_gaps(session, result)
        assert len(gaps) == 1
        gap = gaps[0]
        assert gap.confidence < CONFIDENCE_REVIEW_THRESHOLD
        assert gap.reviewed is False
        assert gap.review_status == "pending"


def test_weak_similarity_leaves_the_gap_unmapped(seeded_db):
    """F5: below LO_MAPPING_THRESHOLD the gap stays unmapped rather than
    being forced onto the closest unrelated outcome."""
    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        gap = SkillGap(
            assessment_result_id=result.id,
            source_evidence_text="laboratory safety induction paperwork was missing",
            severity="medium",
            confidence=0.9,
            reviewed=True,
        )
        session.add(gap)
        session.flush()

        from src.model.silo_mapping import best_similarity

        outcomes = list(result.assessment.subject.learning_outcomes)
        _, similarity = best_similarity(
            gap.source_evidence_text, [o.description for o in outcomes]
        )
        # Fail loudly if this wording starts matching a SILO — a skip would
        # hide that regression and drop the only weak-link assertion.
        assert similarity < LO_MAPPING_THRESHOLD

        assert map_gap_to_learning_outcome(session, gap) is None
        assert gap.learning_outcome_id is None


def test_mastery_formula_is_baseline_minus_severity_times_confidence(seeded_db):
    """F6: the number must be reproducible from the evidence, not opaque."""
    with get_session() as session:
        student = _student(session, "DEMO0001")
        result = _result_for(session, "DEMO0001")
        gaps = extract_skill_gaps(session, result)
        mapped = map_gap_to_learning_outcome(session, gaps[0])
        assert mapped is not None
        assert mapped.code == "SILO2"

        mastery = calculate_mastery_score(session, student, mapped)
        expected = round(
            0.72 - SEVERITY_WEIGHT[gaps[0].severity] * gaps[0].confidence, 4
        )
        assert mastery.score == expected
        assert gaps[0].source_evidence_text in mastery.explanation_text


def test_unreviewed_gap_does_not_change_mastery(seeded_db):
    """Held gaps are evidence for a reviewer, not inputs to the score."""
    with get_session() as session:
        student = _student(session, "DEMO0001")
        result = _result_for(session, "DEMO0001")
        silo1 = session.query(LearningOutcome).filter_by(code="SILO1").one()

        before = calculate_mastery_score(session, student, silo1)
        session.add(
            SkillGap(
                assessment_result_id=result.id,
                learning_outcome_id=silo1.id,
                source_evidence_text="a low-confidence clause held for review",
                severity="high",
                confidence=0.99,
                reviewed=False,
                review_status="pending",
            )
        )
        session.flush()
        after = calculate_mastery_score(session, student, silo1)
        assert after.score == before.score == 0.72


@pytest.mark.skipif(not WORKBOOK.exists(), reason="approved workbook not present")
def test_real_workbook_row_extracts_and_maps_silo_tags(clean_db, monkeypatch):
    """IOG-41 against the approved 150-student file: one low score with
    explicit SILO tags becomes cited, mapped gaps — not TF-IDF guesses."""
    from src.connect import excel_loader

    monkeypatch.setenv("HISTORICAL_DATASET_PATH", str(WORKBOOK.resolve()))
    excel_loader._sheets.cache_clear()
    try:
        results = excel_loader.load_assessment_results()
        outcomes = excel_loader.load_learning_outcomes()
    finally:
        excel_loader._sheets.cache_clear()

    matched = results[
        (results["student_number"] == "STU0001")
        & (results["assessment_name"] == "CSE1OOF - Test")
    ]
    assert not matched.empty, (
        "STU0001 / CSE1OOF - Test is in the approved workbook "
        f"(names were: {sorted(results['assessment_name'].unique())})"
    )
    row = matched.iloc[0]
    assert row["score"] < 80
    assert "SILO1" in row["silo_tags_text"]

    subject_outcomes = outcomes[outcomes["subject_code"] == "CSE1OOF"]

    with get_session() as session:
        subject = Subject(code="CSE1OOF", name="CSE1OOF")
        session.add(subject)
        session.flush()
        for _, outcome in subject_outcomes.iterrows():
            session.add(
                LearningOutcome(
                    subject_id=subject.id,
                    code=outcome["silo_code"],
                    description=outcome["description"],
                )
            )
        assessment = Assessment(subject_id=subject.id, name=str(row["assessment_name"]))
        student = Student(student_number="STU0001", display_name="STU0001")
        session.add_all([assessment, student])
        session.flush()
        weight = None if pd.isna(row["weight"]) else float(row["weight"])
        result = AssessmentResult(
            assessment_id=assessment.id,
            student_id=student.id,
            score=float(row["score"]),
            feedback_text=row["feedback_text"],
            silo_tags_text=row["silo_tags_text"],
            weight=weight,
        )
        session.add(result)
        session.flush()
        session.refresh(result)

        gaps = extract_skill_gaps(session, result)
        assert len(gaps) >= 1
        assert all(g.source_evidence_text.startswith("SILO") for g in gaps)
        assert all(g.reviewed for g in gaps)

        mapped_codes = set()
        for gap in gaps:
            outcome = map_gap_to_learning_outcome(session, gap)
            assert outcome is not None
            mapped_codes.add(outcome.code)
            assert gap.source_evidence_text.startswith(f"{outcome.code}:")
        assert "SILO1" in mapped_codes

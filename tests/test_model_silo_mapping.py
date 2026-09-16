"""Tests for Phase 3 (IOG-37/38): AI-based skill-gap extraction and SILO
mapping (src.model.silo_mapping), checked against the bundled sample
dataset's known feedback text rather than synthetic fixtures - these
three students' feedback was chosen (see data/sample/assessment_results_
sample.csv) specifically to cover "one low-severity gap", "two gaps",
and "zero gaps" in a single small dataset.
"""

from __future__ import annotations
from src.connect.excel_loader import parse_silo_tags
from src.db.database import get_session
from src.db.models import AssessmentResult, LearningOutcome, Student
from src.model.silo_mapping import (
    CONFIDENCE_REVIEW_THRESHOLD,
    MASTERY_THRESHOLD,
    SILO_TAG_CONFIDENCE,
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


# --- Real-dataset path (IOG-33): score-band severity + explicit SILO tags ---
#
# These reuse the sample dataset's own DEMO subject/SILO1-3 fixtures (via
# seeded_db) rather than the real xlsx (gitignored, not present in CI) -
# what's under test here is extract_skill_gaps' *dispatch* and the
# score-band/tag-parsing logic itself, not the loader that populates
# silo_tags_text (that's tests/test_connect_excel_loader.py's job).


def _set_silo_tags(session, student_number: str, silo_tags_text: str, score: float):
    result = _result_for(session, student_number)
    result.silo_tags_text = silo_tags_text
    result.score = score
    session.flush()
    return result


def test_silo_tag_path_is_used_whenever_silo_tags_text_is_set(seeded_db):
    """Setting silo_tags_text switches extraction to the tag-based path
    even though this result's feedback_text still has deficiency markers
    a heuristic scan would otherwise catch - the tag path doesn't look at
    feedback_text at all."""
    with get_session() as session:
        result = _set_silo_tags(session, "DEMO0001", "SILO2: Apply demo techniques", score=40.0)
        gaps = extract_skill_gaps(session, result)

        assert len(gaps) == 1
        gap = gaps[0]
        assert gap.source_evidence_text == "SILO2: Apply demo techniques"
        assert gap.confidence == SILO_TAG_CONFIDENCE
        assert gap.reviewed is True


def test_silo_tag_path_severity_follows_score_bands(seeded_db):
    with get_session() as session:
        high = _set_silo_tags(session, "DEMO0001", "SILO1: gap", score=30.0)
        assert extract_skill_gaps(session, high)[0].severity == "high"

    with get_session() as session:
        medium = _set_silo_tags(session, "DEMO0001", "SILO1: gap", score=60.0)
        assert extract_skill_gaps(session, medium)[0].severity == "medium"

    with get_session() as session:
        low = _set_silo_tags(session, "DEMO0001", "SILO1: gap", score=75.0)
        assert extract_skill_gaps(session, low)[0].severity == "low"


def test_silo_tag_path_at_or_above_mastery_threshold_yields_no_gaps(seeded_db):
    """A High Distinction result isn't a skill gap, even if it's tagged
    with SILOs (every result is tagged with the SILOs it *covers*, not
    the ones the student struggled with)."""
    with get_session() as session:
        result = _set_silo_tags(
            session, "DEMO0001", "SILO1: gap", score=MASTERY_THRESHOLD
        )
        assert extract_skill_gaps(session, result) == []


def test_silo_tag_path_with_no_score_yields_no_gaps(seeded_db):
    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        result.silo_tags_text = "SILO1: gap"
        result.score = None
        session.flush()
        assert extract_skill_gaps(session, result) == []


def test_silo_tag_path_produces_one_gap_per_tagged_silo(seeded_db):
    with get_session() as session:
        result = _set_silo_tags(
            session,
            "DEMO0001",
            "SILO1: Explain core concepts; SILO3: Critically evaluate trade-offs",
            score=55.0,
        )
        gaps = extract_skill_gaps(session, result)
        assert {g.source_evidence_text for g in gaps} == {
            "SILO1: Explain core concepts",
            "SILO3: Critically evaluate trade-offs",
        }


def test_silo_tag_evidence_maps_by_exact_code_not_similarity(seeded_db):
    """The evidence text names its own SILO code - mapping must use that
    exact code, not fall through to a (potentially different) closest
    TF-IDF match."""
    with get_session() as session:
        # Deliberately word this so a naive similarity match might drift
        # towards SILO2 ("Apply...") - the exact "SILO3:" prefix must win.
        result = _set_silo_tags(
            session, "DEMO0001", "SILO3: apply careful technique review", score=55.0
        )
        gap = extract_skill_gaps(session, result)[0]

        outcome = map_gap_to_learning_outcome(session, gap)
        assert outcome is not None
        assert outcome.code == "SILO3"
        assert gap.gap_type == "evaluation"  # SILO3's own verb, not SILO2's


def test_feedback_text_path_still_used_when_silo_tags_text_is_unset(seeded_db):
    """Dispatch check: the sample dataset's results have no silo_tags_text
    (mirrors the real synthetic CSVs, which have no such column), so they
    must still go through the original heuristic unchanged."""
    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        assert result.silo_tags_text is None
        gaps = extract_skill_gaps(session, result)
        assert len(gaps) == 1
        assert gaps[0].confidence != SILO_TAG_CONFIDENCE

def test_parse_silo_tags_normalises_case_and_whitespace():
    result = parse_silo_tags("  silo1:  Understands DNA replication  ")

    assert result == [("SILO1", "Understands DNA replication")]


def test_parse_silo_tags_skips_malformed_segments_but_keeps_valid_segments():
    result = parse_silo_tags(
        "SILO1: Understands DNA replication; malformed segment; SILO2: Applies PCR"
    )

    assert result == [
        ("SILO1", "Understands DNA replication"),
        ("SILO2", "Applies PCR"),
    ]


def test_parse_silo_tags_skips_empty_descriptions():
    result = parse_silo_tags(
        "SILO1: ; SILO2: Applies PCR; SILO3:"
    )

    assert result == [("SILO2", "Applies PCR")]


def test_parse_silo_tags_returns_empty_list_for_only_malformed_input():
    result = parse_silo_tags("not a silo tag; another malformed segment")

    assert result == []

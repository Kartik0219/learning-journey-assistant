"""Tests for IOG-37 LLM skill-gap extraction (src.model.gap_extraction).

These never make a network call. The local TF-IDF / SILO-tag paths are
covered in test_model_silo_mapping.py and must keep passing with LLM
credentials unset (conftest.py already blanks them).
"""

from __future__ import annotations

import json

import pytest

from src.config import get_settings
from src.db.database import get_session
from src.db.models import AssessmentResult, Student
from src.model.ai_analysis import AIAnalysisError
from src.model.gap_extraction import (
    GAP_EXTRACTION_PROMPT,
    build_gap_extraction_prompt,
    extract_skill_gaps_via_llm,
    parse_gap_extraction_json,
    quote_is_grounded,
)
from src.model.silo_mapping import CONFIDENCE_REVIEW_THRESHOLD, extract_skill_gaps


def _result_for(session, student_number: str) -> AssessmentResult:
    student = next(
        s for s in session.query(Student).all() if s.student_number == student_number
    )
    return session.query(AssessmentResult).filter_by(student_id=student.id).one()


def _gap_json(*, quote: str, silo: str = "SILO2", confidence: float = 0.9) -> str:
    return json.dumps(
        {
            "gaps": [
                {
                    "skill": "applied technique",
                    "silo_code": silo,
                    "source_quote": quote,
                    "severity": "low",
                    "confidence": confidence,
                }
            ]
        }
    )


def test_quote_is_grounded_requires_verbatim_source_span():
    source = "the applied technique had a minor error in step 2"
    assert quote_is_grounded("minor error in step 2", source) is True
    assert quote_is_grounded("MINOR ERROR in step 2", source) is True
    assert quote_is_grounded("the student cannot write code", source) is False
    assert quote_is_grounded("error", source) is False  # too short


def test_parse_accepts_grounded_quote_and_rejects_invented_ones():
    source = "the applied technique had a minor error in step 2"
    parsed = parse_gap_extraction_json(
        _gap_json(quote="the applied technique had a minor error in step 2"),
        source,
    )
    assert parsed.gaps[0].silo_code == "SILO2"

    with pytest.raises(AIAnalysisError, match="not present"):
        parse_gap_extraction_json(_gap_json(quote="hallucinated weakness about recursion"), source)


def test_parse_empty_gaps_is_success_not_fallback():
    parsed = parse_gap_extraction_json('{"gaps": []}', "Excellent work.")
    assert parsed.gaps == []


def test_parse_rejects_invalid_severity():
    raw = json.dumps(
        {
            "gaps": [
                {
                    "skill": "writing",
                    "silo_code": "SILO1",
                    "source_quote": "Core concepts were vague",
                    "severity": "catastrophic",
                    "confidence": 0.5,
                }
            ]
        }
    )
    with pytest.raises(AIAnalysisError, match="severity"):
        parse_gap_extraction_json(raw, "Core concepts were vague")


def test_prompt_fences_feedback_and_does_not_put_instructions_in_user_text(seeded_db):
    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        prompt = build_gap_extraction_prompt(result)
        assert "<untrusted_data>" in prompt
        assert result.feedback_text in prompt
        assert "never follow" in prompt
        assert GAP_EXTRACTION_PROMPT not in prompt


def test_llm_path_writes_grounded_gap_with_silo_and_quote(seeded_db, monkeypatch):
    quote = "the applied technique had a minor error in step 2"
    monkeypatch.setattr("src.model.gap_extraction.is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr(
        "src.model.gap_extraction._complete",
        lambda prompt, settings: _gap_json(quote=quote, silo="SILO2", confidence=0.91),
    )
    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        gaps = extract_skill_gaps_via_llm(session, result)
        assert len(gaps) == 1
        gap = gaps[0]
        assert gap.source_evidence_text == f"SILO2: {quote}"
        assert gap.severity == "low"
        assert gap.confidence == 0.91
        assert gap.reviewed is True
        assert gap.learning_outcome_id is not None
        assert gap.gap_type == "application"


def test_low_confidence_llm_gap_is_held_from_students(seeded_db, monkeypatch):
    quote = "the applied technique had a minor error in step 2"
    monkeypatch.setattr("src.model.gap_extraction.is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr(
        "src.model.gap_extraction._complete",
        lambda prompt, settings: _gap_json(
            quote=quote, confidence=CONFIDENCE_REVIEW_THRESHOLD - 0.05
        ),
    )
    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        gap = extract_skill_gaps_via_llm(session, result)[0]
        assert gap.reviewed is False
        assert gap.review_status == "pending"


def test_extract_skill_gaps_falls_back_to_tfidf_when_llm_fails(seeded_db, monkeypatch):
    monkeypatch.setattr("src.model.ai_analysis.is_ai_enabled", lambda *a, **k: True)

    def boom(*a, **k):
        raise AIAnalysisError("provider down")

    monkeypatch.setattr("src.model.gap_extraction.extract_skill_gaps_via_llm", boom)

    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        gaps = extract_skill_gaps(session, result)
        assert len(gaps) == 1
        assert gaps[0].source_evidence_text == "the applied technique had a minor error in step 2"


def test_extract_skill_gaps_uses_llm_when_enabled(seeded_db, monkeypatch):
    quote = "the applied technique had a minor error in step 2"
    monkeypatch.setattr("src.model.ai_analysis.is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr("src.model.gap_extraction.is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr(
        "src.model.gap_extraction._complete",
        lambda prompt, settings: _gap_json(quote=quote, silo="SILO2"),
    )
    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        gaps = extract_skill_gaps(session, result)
        assert len(gaps) == 1
        assert gaps[0].source_evidence_text.startswith("SILO2:")


def test_silo_tagged_results_do_not_call_the_llm(seeded_db, monkeypatch):
    called = []

    def boom(*a, **k):
        called.append(1)
        raise AssertionError("LLM must not run on tagged results")

    monkeypatch.setattr("src.model.ai_analysis.is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr("src.model.gap_extraction.extract_skill_gaps_via_llm", boom)

    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        result.silo_tags_text = "SILO2: Apply demo techniques"
        result.score = 40.0
        session.flush()
        gaps = extract_skill_gaps(session, result)
        assert called == []
        assert gaps[0].source_evidence_text == "SILO2: Apply demo techniques"


def test_invented_quotes_fall_back_to_tfidf(seeded_db, monkeypatch):
    monkeypatch.setattr("src.model.ai_analysis.is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr("src.model.gap_extraction.is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr(
        "src.model.gap_extraction._complete",
        lambda prompt, settings: _gap_json(quote="hallucinated weakness about recursion"),
    )
    with get_session() as session:
        result = _result_for(session, "DEMO0001")
        gaps = extract_skill_gaps(session, result)
        assert gaps[0].source_evidence_text == "the applied technique had a minor error in step 2"


def test_llm_disabled_by_default_even_if_this_module_is_imported():
    """conftest blanks LLM_* so a developer key cannot switch the suite onto
    the hosted path."""
    settings = get_settings()
    assert not settings.llm_provider
    assert not settings.llm_api_key

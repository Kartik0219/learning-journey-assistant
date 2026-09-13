"""Tests for IOG-52/IOG-54: the opt-in AI insight Deliver view
(src.deliver.ai_insight_api.get_ai_insight).

No network: the provider is monkeypatched. These prove the page is safe by
default (off, no credentials -> nothing generated, dashboard stays the source
of truth), respects the same N6/N2 gate as the rest of the Deliver layer, and
renders a provider's output when one is configured.
"""

from __future__ import annotations

import pytest

from src.deliver import ai_insight_api
from src.db.database import get_session
from src.db.models import Student
from src.model.ai_analysis import DiagnosticResult
from src.security.authorization import Actor, AuthorizationError, Role
from src.security.consent import ConsentError, record_consent


@pytest.fixture(autouse=True)
def _fresh_insight_cache():
    """The insight cache is per process; never let one test's result leak
    into another's."""
    ai_insight_api.clear_insight_cache()
    yield
    ai_insight_api.clear_insight_cache()


def _student(session, student_number: str) -> Student:
    return next(
        s for s in session.query(Student).all() if s.student_number == student_number
    )


_STUB = DiagnosticResult(
    learningOutcomes=[
        {
            "code": "SILO2",
            "title": "Apply demo techniques",
            "status": "Focus Area",
            "masteryPercentage": 55,
            "evidenceQuote": "the applied technique had a minor error in step 2",
        }
    ],
    strengths=["Solid grasp of core concepts (SILO1)."],
    focusAreas=[
        {
            "topic": "Apply demo techniques",
            "recommendedStep": "Redo one worked example and self-check.",
            "resourceLinkOrModule": "Worked Technique Walkthrough",
        }
    ],
    disclaimer="Diagnostic only; does not alter official grades.",
)


def test_insight_disabled_when_no_provider(seeded_db):
    """Default state (no LLM_PROVIDER): enabled=False, nothing generated."""
    with get_session() as session:
        student = _student(session, "DEMO0001")
        data = ai_insight_api.get_ai_insight(
            session, Actor(role=Role.STUDENT, student_id=student.id), student.id
        )
        assert data["enabled"] is False
        assert data["insight"] is None
        assert data["error"] is None


def test_insight_returned_when_provider_enabled(seeded_db, monkeypatch):
    monkeypatch.setattr(ai_insight_api, "is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr(ai_insight_api, "analyze_student", lambda *a, **k: _STUB)

    with get_session() as session:
        student = _student(session, "DEMO0001")
        data = ai_insight_api.get_ai_insight(
            session, Actor(role=Role.STUDENT, student_id=student.id), student.id
        )
        assert data["enabled"] is True
        assert data["error"] is None
        assert data["insight"]["learningOutcomes"][0]["code"] == "SILO2"
        assert data["insight"]["focusAreas"][0]["topic"] == "Apply demo techniques"


def test_insight_reports_provider_error_without_crashing(seeded_db, monkeypatch):
    def _boom(*a, **k):
        raise ai_insight_api.AIAnalysisError("provider returned junk")

    monkeypatch.setattr(ai_insight_api, "is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr(ai_insight_api, "analyze_student", _boom)

    with get_session() as session:
        student = _student(session, "DEMO0001")
        data = ai_insight_api.get_ai_insight(
            session, Actor(role=Role.STUDENT, student_id=student.id), student.id
        )
        assert data["enabled"] is True
        assert data["insight"] is None
        assert "junk" in data["error"]


def test_insight_blocks_cross_student_access(seeded_db):
    """N6: a Student actor may not open another student's insight."""
    with get_session() as session:
        me = _student(session, "DEMO0001")
        other = _student(session, "DEMO0002")
        with pytest.raises(AuthorizationError):
            ai_insight_api.get_ai_insight(
                session, Actor(role=Role.STUDENT, student_id=me.id), other.id
            )


def test_insight_blocked_without_active_consent(seeded_db, monkeypatch):
    """N2: no analysis for a student whose consent is withdrawn."""
    monkeypatch.setattr(ai_insight_api, "is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr(ai_insight_api, "analyze_student", lambda *a, **k: _STUB)

    with get_session() as session:
        student = _student(session, "DEMO0001")
        record_consent(session, student, given=False)  # withdraw
        with pytest.raises(ConsentError):
            ai_insight_api.get_ai_insight(
                session, Actor(role=Role.STUDENT, student_id=student.id), student.id
            )


def test_successful_insight_is_cached_so_reloads_do_not_call_the_provider(
    seeded_db, monkeypatch
):
    calls = []

    def _counting(*a, **k):
        calls.append(1)
        return _STUB

    monkeypatch.setattr(ai_insight_api, "is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr(ai_insight_api, "analyze_student", _counting)

    with get_session() as session:
        student = _student(session, "DEMO0001")
        actor = Actor(role=Role.STUDENT, student_id=student.id)
        first = ai_insight_api.get_ai_insight(session, actor, student.id)
        second = ai_insight_api.get_ai_insight(session, actor, student.id)

    assert len(calls) == 1
    assert second["insight"] == first["insight"]


def test_cache_expires(seeded_db, monkeypatch):
    calls = []
    clock = [1000.0]

    monkeypatch.setattr(ai_insight_api.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(ai_insight_api, "is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr(ai_insight_api, "analyze_student", lambda *a, **k: calls.append(1) or _STUB)

    with get_session() as session:
        student = _student(session, "DEMO0001")
        actor = Actor(role=Role.STUDENT, student_id=student.id)
        ai_insight_api.get_ai_insight(session, actor, student.id)
        clock[0] += ai_insight_api.INSIGHT_CACHE_SECONDS + 1
        ai_insight_api.get_ai_insight(session, actor, student.id)

    assert len(calls) == 2


def test_cache_never_bypasses_access_control(seeded_db, monkeypatch):
    """N6 is checked before the cache: a cached insight for DEMO0002 must not
    be reachable by DEMO0001."""
    monkeypatch.setattr(ai_insight_api, "is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr(ai_insight_api, "analyze_student", lambda *a, **k: _STUB)

    with get_session() as session:
        me = _student(session, "DEMO0001")
        other = _student(session, "DEMO0002")
        ai_insight_api.get_ai_insight(  # DEMO0002 warms the cache for themself
            session, Actor(role=Role.STUDENT, student_id=other.id), other.id
        )
        with pytest.raises(AuthorizationError):
            ai_insight_api.get_ai_insight(
                session, Actor(role=Role.STUDENT, student_id=me.id), other.id
            )


def test_rate_limit_shows_a_friendly_busy_message_and_is_not_cached(seeded_db, monkeypatch):
    def _limited(*a, **k):
        raise ai_insight_api.AIRateLimited("Gemini rate limit (HTTP 429)")

    monkeypatch.setattr(ai_insight_api, "is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr(ai_insight_api, "analyze_student", _limited)

    with get_session() as session:
        student = _student(session, "DEMO0001")
        actor = Actor(role=Role.STUDENT, student_id=student.id)
        data = ai_insight_api.get_ai_insight(session, actor, student.id)
        assert data["error"].startswith("The AI service is busy")
        assert data["insight"] is None

        monkeypatch.setattr(ai_insight_api, "analyze_student", lambda *a, **k: _STUB)
        assert ai_insight_api.get_ai_insight(session, actor, student.id)["insight"] is not None


def test_daily_quota_says_it_resets_rather_than_try_in_a_minute(seeded_db, monkeypatch):
    def _daily(*a, **k):
        raise ai_insight_api.AIRateLimited("Gemini daily free-tier quota is used up")

    monkeypatch.setattr(ai_insight_api, "is_ai_enabled", lambda *a, **k: True)
    monkeypatch.setattr(ai_insight_api, "analyze_student", _daily)

    with get_session() as session:
        student = _student(session, "DEMO0001")
        data = ai_insight_api.get_ai_insight(
            session, Actor(role=Role.STUDENT, student_id=student.id), student.id
        )
    assert "resets within 24 hours" in data["error"]
    assert "try again in a minute" not in data["error"]

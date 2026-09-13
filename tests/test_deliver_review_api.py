"""Tests for the staff skill-gap review queue (src.deliver.review_api).

These cover the thing F4 actually asks for - that a *person* checks a
low-confidence gap before a student sees it - plus F5's "teaching staff
can correct those links", N6 (server-side authorization) and N4 (every
decision audited).
"""

from __future__ import annotations

import pytest

from src.db.database import get_session
from src.db.models import (
    AssessmentResult,
    AuditLogEntry,
    LearningOutcome,
    SkillGap,
    Subject,
)
from src.deliver.review_api import (
    ReviewError,
    get_review_queue,
    review_gap,
)
from src.security.authorization import Actor, AuthorizationError, Role

STAFF = Actor(role=Role.STAFF)
ADMIN = Actor(role=Role.ADMIN)


def _student_actor(session) -> Actor:
    from src.db.models import Student

    student = session.query(Student).first()
    return Actor(role=Role.STUDENT, student_id=student.id)


def _make_gaps(session) -> None:
    """Put one held-back gap and one auto-approved gap on the first seeded
    assessment result.

    Built directly rather than by running the Model stage: the small test
    fixture's feedback happens to score 0.20-0.30 against its rubric, i.e.
    above CONFIDENCE_REVIEW_THRESHOLD, so extraction produces nothing
    pending. Pinning the confidences here means these tests exercise the
    review gate itself and cannot be silently disarmed by someone later
    retuning the fixture text or the threshold.
    """
    result = session.query(AssessmentResult).first()
    lo = (
        session.query(LearningOutcome)
        .filter_by(subject_id=result.assessment.subject_id)
        .order_by(LearningOutcome.code)
        .first()
    )
    session.add_all(
        [
            SkillGap(
                assessment_result_id=result.id,
                learning_outcome_id=lo.id,
                source_evidence_text="the trade-off analysis was one-sided",
                severity="medium",
                confidence=0.08,
                reviewed=False,
                review_status="pending",
            ),
            SkillGap(
                assessment_result_id=result.id,
                learning_outcome_id=lo.id,
                source_evidence_text="core concepts were vague",
                severity="high",
                confidence=0.42,
                reviewed=True,
                review_status="auto_approved",
            ),
        ]
    )
    session.flush()


def _pending_gap(session) -> SkillGap:
    return session.query(SkillGap).filter(SkillGap.review_status == "pending").first()


# --- N6: server-side authorization ----------------------------------------


def test_student_cannot_view_the_queue(seeded_db):
    with get_session() as session:
        _make_gaps(session)
        with pytest.raises(AuthorizationError):
            get_review_queue(session, _student_actor(session))


def test_student_cannot_decide_a_gap(seeded_db):
    """The N6 case that matters: a student POSTing straight at the endpoint,
    bypassing whatever the UI does or does not render for them."""
    with get_session() as session:
        _make_gaps(session)
        gap = _pending_gap(session)
        assert gap is not None
        with pytest.raises(AuthorizationError):
            review_gap(session, _student_actor(session), gap.id, "approve")
        session.refresh(gap)
        assert gap.review_status == "pending"
        assert gap.reviewed is False


def test_staff_and_admin_may_view_the_queue(seeded_db):
    with get_session() as session:
        _make_gaps(session)
        for actor in (STAFF, ADMIN):
            queue = get_review_queue(session, actor)
            assert "pending" in queue


# --- F4: the queue holds exactly what was withheld ------------------------


def test_queue_contains_only_pending_gaps(seeded_db):
    with get_session() as session:
        _make_gaps(session)
        queue = get_review_queue(session, STAFF)
        assert queue["pending"], "expected the fixture to produce held-back gaps"
        for row in queue["pending"]:
            assert row["review_status"] == "pending"
        # Auto-approved gaps passed triage and were never withheld, so they
        # must not appear as work for a human.
        ids = {row["id"] for row in queue["pending"]}
        auto = session.query(SkillGap).filter_by(review_status="auto_approved").all()
        assert ids.isdisjoint({g.id for g in auto})


def test_queue_rows_carry_the_evidence_line(seeded_db):
    """F4: a reviewer decides from the source line, never from a bare
    assertion that a gap exists."""
    with get_session() as session:
        _make_gaps(session)
        for row in get_review_queue(session, STAFF)["pending"]:
            assert row["evidence"].strip()
            assert 0.0 <= row["confidence"] <= 1.0


def test_approve_makes_the_gap_visible_to_the_student(seeded_db):
    with get_session() as session:
        _make_gaps(session)
        gap = _pending_gap(session)
        gap_id = gap.id
        review_gap(session, STAFF, gap_id, "approve")

        refreshed = session.get(SkillGap, gap_id)
        assert refreshed.review_status == "approved"
        assert refreshed.reviewed is True
        assert refreshed.reviewed_by == "staff"
        assert refreshed.reviewed_at is not None


def test_reject_keeps_the_gap_hidden_and_out_of_the_queue(seeded_db):
    """A rejected gap must not reappear for review, and must never become
    visible to the student - the failure mode before review_status existed
    was that `reviewed=False` meant both 'pending' and 'rejected'."""
    with get_session() as session:
        _make_gaps(session)
        gap = _pending_gap(session)
        gap_id = gap.id
        review_gap(session, STAFF, gap_id, "reject")

        refreshed = session.get(SkillGap, gap_id)
        assert refreshed.review_status == "rejected"
        assert refreshed.reviewed is False

        queue_ids = {row["id"] for row in get_review_queue(session, STAFF)["pending"]}
        assert gap_id not in queue_ids


def test_decided_gap_leaves_the_pending_count(seeded_db):
    with get_session() as session:
        _make_gaps(session)
        before = get_review_queue(session, STAFF)["counts"]["pending"]
        review_gap(session, STAFF, _pending_gap(session).id, "approve")
        after = get_review_queue(session, STAFF)["counts"]["pending"]
        assert after == before - 1


def test_unknown_decision_is_rejected(seeded_db):
    with get_session() as session:
        _make_gaps(session)
        gap = _pending_gap(session)
        with pytest.raises(ReviewError):
            review_gap(session, STAFF, gap.id, "maybe")
        session.refresh(gap)
        assert gap.review_status == "pending"


def test_unknown_gap_is_rejected(seeded_db):
    with get_session() as session:
        _make_gaps(session)
        with pytest.raises(ReviewError):
            review_gap(session, STAFF, 999_999, "approve")


# --- F5: staff can correct the SILO link ----------------------------------


def test_reviewer_can_reassign_the_learning_outcome(seeded_db):
    with get_session() as session:
        _make_gaps(session)
        gap = _pending_gap(session)
        gap_id = gap.id
        subject_id = gap.assessment_result.assessment.subject_id
        target = (
            session.query(LearningOutcome)
            .filter(
                LearningOutcome.subject_id == subject_id,
                LearningOutcome.id != gap.learning_outcome_id,
            )
            .first()
        )
        assert target is not None

        review_gap(session, STAFF, gap_id, "approve", learning_outcome_id=target.id)
        assert session.get(SkillGap, gap_id).learning_outcome_id == target.id


def test_cannot_reassign_to_another_subjects_outcome(seeded_db):
    """F5 lets staff correct a link, not invent a cross-subject one."""
    with get_session() as session:
        _make_gaps(session)
        gap = _pending_gap(session)
        gap_subject_id = gap.assessment_result.assessment.subject_id

        other_subject = Subject(code="OTHER101", name="Another Subject")
        session.add(other_subject)
        session.flush()
        foreign = LearningOutcome(
            subject_id=other_subject.id, code="OTHER-SILO1", description="Unrelated"
        )
        session.add(foreign)
        session.flush()
        assert other_subject.id != gap_subject_id

        with pytest.raises(ReviewError):
            review_gap(session, STAFF, gap.id, "approve", learning_outcome_id=foreign.id)


def test_reassignment_alone_does_not_decide_the_gap(seeded_db):
    """A rejected ReviewError must leave the row untouched - no half-applied
    reassignment without a recorded decision."""
    with get_session() as session:
        _make_gaps(session)
        gap = _pending_gap(session)
        original_lo = gap.learning_outcome_id
        with pytest.raises(ReviewError):
            review_gap(session, STAFF, gap.id, "not-a-decision", learning_outcome_id=1)
        session.refresh(gap)
        assert gap.learning_outcome_id == original_lo
        assert gap.review_status == "pending"


# --- N4: every decision is audited ----------------------------------------


def test_decision_writes_an_audit_row(seeded_db):
    with get_session() as session:
        _make_gaps(session)
        gap_id = _pending_gap(session).id
        review_gap(session, STAFF, gap_id, "approve")

        entry = (
            session.query(AuditLogEntry)
            .filter(AuditLogEntry.action == "skill_gap_approved")
            .order_by(AuditLogEntry.id.desc())
            .first()
        )
        assert entry is not None
        assert entry.actor == "staff"
        assert f"skill_gap:{gap_id}" in entry.target


def test_audit_row_records_a_silo_correction(seeded_db):
    """N4 + F5: the correction has to be reconstructable from the audit log
    alone, not just visible in the current row."""
    with get_session() as session:
        _make_gaps(session)
        gap = _pending_gap(session)
        gap_id = gap.id
        original_lo = gap.learning_outcome_id
        target = (
            session.query(LearningOutcome)
            .filter(
                LearningOutcome.subject_id == gap.assessment_result.assessment.subject_id,
                LearningOutcome.id != original_lo,
            )
            .first()
        )
        review_gap(session, STAFF, gap_id, "approve", learning_outcome_id=target.id)

        entry = (
            session.query(AuditLogEntry)
            .filter(AuditLogEntry.action == "skill_gap_approved")
            .order_by(AuditLogEntry.id.desc())
            .first()
        )
        assert f"silo:{original_lo}->{target.id}" in entry.target


def test_rejection_is_audited_distinctly(seeded_db):
    with get_session() as session:
        _make_gaps(session)
        review_gap(session, STAFF, _pending_gap(session).id, "reject")
        assert (
            session.query(AuditLogEntry)
            .filter(AuditLogEntry.action == "skill_gap_rejected")
            .count()
            == 1
        )


# --- F12: reviewing never touches a grade ---------------------------------


def test_review_does_not_change_any_assessment_result(seeded_db):
    with get_session() as session:
        _make_gaps(session)
        gap = _pending_gap(session)
        result = gap.assessment_result
        before = (result.id, result.score, result.feedback_text)

        review_gap(session, STAFF, gap.id, "approve")

        after = session.get(type(result), before[0])
        assert (after.id, after.score, after.feedback_text) == before

"""Staff review queue for extracted skill gaps (F4, F5).

This module is what makes F4 true as written. The requirement is:

    "Every extracted gap must point to a line in the rubric or feedback.
     Items with low confidence are held for review and are not shown to
     the student until checked."

Before this existed, `SkillGap.reviewed` was set once, at extraction
time, by `confidence >= CONFIDENCE_REVIEW_THRESHOLD`, and nothing ever
changed it again. So "checked" was a float comparison: anything above the
line was published to the student with no human involved, and anything
below it was withheld permanently with no queue, no screen, and no way
out. The field was named `reviewed`, which made the code read as
compliant while no review existed. A threshold is triage, not a check.

It is also the second half of F5:

    "Link gaps to learning outcomes and subject resources using text
     embeddings and similarity scores. *Teaching staff can correct those
     links.*"

`src.deliver.coordinator_api` reports on links but cannot change one.
`review_gap()` here can: reassigning the learning outcome is one of the
decisions a reviewer can record.

Compliance gates, matching the rest of Deliver:
  - N6 (authorization): Staff/Admin only. A Student actor raises
    AuthorizationError, the same type `require_student_access` raises, so
    `src.deliver.app` handles it identically. The decision is always
    attributed to the *server-authenticated* actor, never to anything the
    client sent.
  - N4 (audit): every decision writes an append-only audit row through
    `src.security.audit.log_event` - who, what, which gap, and the SILO
    reassignment if there was one. A review gate whose decisions leave no
    trace is not a control anybody can verify.
  - F12: this only ever writes to `SkillGap` review columns. No official
    grade, score or assessment result is touched.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from src.db.models import LearningOutcome, SkillGap
from src.security.audit import log_event
from src.security.authorization import Actor, AuthorizationError, Role

# The decisions a human reviewer can record. "pending" and "auto_approved"
# are states a gap arrives in, not decisions anyone can make, so they are
# deliberately absent here.
REVIEW_DECISIONS = ("approve", "reject")

# Statuses that mean "a human has dealt with this"; anything else is still
# queue-able.
_DECIDED_STATUSES = ("approved", "rejected")


class ReviewError(ValueError):
    """Raised when a review request is malformed - unknown gap, unknown
    decision, or a learning outcome that doesn't belong to the gap's
    subject. Distinct from AuthorizationError: this is a bad request, not
    a forbidden one."""


def _require_staff(actor: Actor, action: str) -> None:
    """N6: the review queue is a Staff/Admin control surface. Checked on
    the server for every call, regardless of what any client renders."""
    if actor.role == Role.STUDENT:
        raise AuthorizationError(
            f"Only Staff/Admin may {action} - a Student actor has no access "
            "to the skill-gap review queue (N6)."
        )


def _gap_payload(gap: SkillGap) -> dict:
    """One queue row. Carries the evidence text and confidence so a
    reviewer decides from the source line (F4), never from a bare
    assertion that a gap exists."""
    result = gap.assessment_result
    return {
        "id": gap.id,
        "evidence": gap.source_evidence_text,
        "severity": gap.severity,
        "confidence": gap.confidence,
        "confidence_pct": round(gap.confidence * 100, 1),
        "review_status": gap.review_status,
        "reviewed_by": gap.reviewed_by,
        "reviewed_at": gap.reviewed_at.isoformat() if gap.reviewed_at else None,
        "student_display_name": result.student.display_name,
        "assessment_name": result.assessment.name,
        "subject_code": result.assessment.subject.code,
        "subject_id": result.assessment.subject.id,
        "learning_outcome_id": gap.learning_outcome_id,
        "learning_outcome_code": (
            gap.learning_outcome.code if gap.learning_outcome else None
        ),
    }


def get_review_queue(session: Session, actor: Actor, limit: int = 100) -> dict:
    """N6: Staff/Admin only. The gaps F4 is holding back, oldest first.

    Lowest confidence first, because those are the ones the extractor was
    least sure about and where a human adds the most. Each row ships the
    learning outcomes available for reassignment (F5), scoped to the gap's
    own subject - a SILO from another subject is never a valid link.
    """
    _require_staff(actor, "view the review queue")

    pending = (
        session.query(SkillGap)
        .filter(SkillGap.review_status == "pending")
        .order_by(SkillGap.confidence.asc(), SkillGap.id.asc())
        .limit(limit)
        .all()
    )

    outcomes_by_subject: dict[int, list[dict]] = {}
    rows = []
    for gap in pending:
        payload = _gap_payload(gap)
        subject_id = payload["subject_id"]
        if subject_id not in outcomes_by_subject:
            outcomes_by_subject[subject_id] = [
                {"id": lo.id, "code": lo.code, "description": lo.description}
                for lo in session.query(LearningOutcome)
                .filter_by(subject_id=subject_id)
                .order_by(LearningOutcome.code)
                .all()
            ]
        payload["available_outcomes"] = outcomes_by_subject[subject_id]
        rows.append(payload)

    decided = (
        session.query(SkillGap)
        .filter(SkillGap.review_status.in_(_DECIDED_STATUSES))
        .order_by(SkillGap.reviewed_at.desc())
        .limit(10)
        .all()
    )

    return {
        "pending": rows,
        "pending_total": session.query(SkillGap)
        .filter(SkillGap.review_status == "pending")
        .count(),
        "recently_decided": [_gap_payload(g) for g in decided],
        "counts": {
            status: session.query(SkillGap)
            .filter(SkillGap.review_status == status)
            .count()
            for status in ("pending", "auto_approved", "approved", "rejected")
        },
    }


def review_gap(
    session: Session,
    actor: Actor,
    gap_id: int,
    decision: str,
    learning_outcome_id: int | None = None,
) -> dict:
    """Record one human review decision (F4), optionally correcting the
    gap's learning-outcome link on the way through (F5).

    `approve` sets `reviewed=True`, which is what makes the gap visible to
    the student. `reject` leaves `reviewed` False and moves the gap out of
    the queue, so a rejected item is neither shown nor offered again.

    The decision is attributed to `actor`, the role the server
    authenticated - not to any identifier the client supplied (N6) - and
    written to the append-only audit log (N4).
    """
    _require_staff(actor, "review a skill gap")

    if decision not in REVIEW_DECISIONS:
        raise ReviewError(
            f"Unknown review decision {decision!r}; expected one of {REVIEW_DECISIONS}."
        )

    gap = session.get(SkillGap, gap_id)
    if gap is None:
        raise ReviewError(f"No skill gap with id={gap_id}.")

    reassigned_from = gap.learning_outcome_id
    if learning_outcome_id is not None and learning_outcome_id != gap.learning_outcome_id:
        outcome = session.get(LearningOutcome, learning_outcome_id)
        if outcome is None:
            raise ReviewError(f"No learning outcome with id={learning_outcome_id}.")
        # F5 lets staff correct a link, not invent a cross-subject one: the
        # SILO must belong to the subject this result was assessed under.
        gap_subject_id = gap.assessment_result.assessment.subject_id
        if outcome.subject_id != gap_subject_id:
            raise ReviewError(
                f"Learning outcome {outcome.code} belongs to subject "
                f"id={outcome.subject_id}, but this gap was assessed under "
                f"subject id={gap_subject_id}."
            )
        gap.learning_outcome_id = learning_outcome_id

    gap.review_status = "approved" if decision == "approve" else "rejected"
    gap.reviewed = decision == "approve"
    gap.reviewed_by = actor.role.value
    gap.reviewed_at = dt.datetime.now(dt.timezone.utc)

    # N4: the decision, and any SILO correction, both have to be reconstructable
    # from the audit log alone.
    target = f"skill_gap:{gap.id}"
    if reassigned_from != gap.learning_outcome_id:
        target += f" silo:{reassigned_from}->{gap.learning_outcome_id}"
    log_event(
        session,
        actor=actor.role.value,
        action=f"skill_gap_{gap.review_status}",
        target=target,
    )

    session.flush()
    return _gap_payload(gap)

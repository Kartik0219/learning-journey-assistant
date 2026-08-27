"""Consent gating (N2): "If consent is withdrawn, stop further
processing for that student" - enforced here, not left to each caller
to remember.

`ConsentRecord.is_active` (src/db/models.py) already encodes the rule;
this module is what makes it a gate instead of just a flag nobody
checks. Every stage that touches student-level data beyond basic
identity provisioning (skill-gap extraction, mastery scoring, the
dashboard, study-plan/quiz generation) should call
`ensure_consent_active()` before doing anything with that student's
rows, and `record_consent()` when consent is given or withdrawn so the
change is both persisted and audit-logged in one call - see N4.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from src.db.models import ConsentRecord, Student
from src.security.audit import log_event


class ConsentError(PermissionError):
    """Raised when a pipeline stage tries to process a student who has
    not given active consent."""


def ensure_consent_active(session: Session, student_id: int) -> None:
    """Raise ConsentError unless this student has active consent.

    No ConsentRecord at all is treated the same as consent not given -
    the default must be "don't process", never "assume yes".
    """
    record = session.query(ConsentRecord).filter_by(student_id=student_id).one_or_none()
    if record is None or not record.is_active:
        raise ConsentError(
            f"student_id={student_id} does not have active consent; "
            "processing must not proceed."
        )


def record_consent(session: Session, student: Student, given: bool) -> ConsentRecord:
    """Set a student's consent state and audit-log the change in one call,
    so the two can never drift apart (N2 + N4 together)."""
    now = dt.datetime.now(dt.timezone.utc)
    record = session.query(ConsentRecord).filter_by(student_id=student.id).one_or_none()
    if record is None:
        record = ConsentRecord(student_id=student.id)
        session.add(record)

    record.consent_given = given
    if given:
        record.consent_date = now
        record.withdrawn_date = None
        log_event(
            session,
            actor=student.student_number,
            action="consent_given",
            target=student.student_number,
        )
    else:
        record.withdrawn_date = now
        log_event(
            session,
            actor=student.student_number,
            action="consent_withdrawn",
            target=student.student_number,
        )

    return record

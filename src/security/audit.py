"""Audit logging (N4): "log sign-in, consent changes, data import, and
study-plan/quiz creation."

`AuditLogEntry` (src/db/models.py) is append-only by convention - this
module is the *only* place that should construct one, so there is a
single, consistent write path instead of every caller building rows by
hand. `log_event()` adds to the current session but does not commit;
callers are expected to be inside a `get_session()` block that commits
on exit (src/db/database.py), the same pattern the rest of the pipeline
uses.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.db.models import AuditLogEntry


def log_event(
    session: Session, actor: str, action: str, target: str | None = None
) -> AuditLogEntry:
    """Record one audit event. `actor` is a student_number or "system";
    `action` is a short machine-readable label (see the examples on
    `AuditLogEntry` in src/db/models.py: "consent_given", "data_import",
    "sign_in", "quiz_created", ...); `target` is whatever the action was
    performed on (a student_number, a dataset name, etc.)."""
    entry = AuditLogEntry(actor=actor, action=action, target=target)
    session.add(entry)
    return entry

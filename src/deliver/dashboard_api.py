"""Phase 4/6 (IOG-40, IOG-31 tickets) - not yet implemented.

Owns the student-facing dashboard (F10): mastery by learning outcome,
priority topics, study plan, quizzes, and resource links, scoped to the
logged-in student only (N6 - "one student cannot open another student's
records"). Whatever web framework the team picks (FastAPI is a
reasonable free-tier-friendly default, per the tender's Price and
Budget section - not decided yet) goes in requirements.txt when this
ticket starts, not before, so Phase 1 doesn't carry a dependency nobody
is using yet.

IOG-42 (Phase 5) contract this must follow once it's built: call
`require_student_access` and `ensure_consent_active` (src.security)
*before* touching any of this student's rows - both already raise the
right error type on their own, there is no need to catch and re-wrap
them here.
"""

from sqlalchemy.orm import Session

from src.security.authorization import Actor, require_student_access
from src.security.consent import ensure_consent_active


def get_student_dashboard(session: Session, actor: Actor, student_id: int, *args, **kwargs):
    """Placeholder entry point - implement as part of IOG-40.

    The two security checks below are not placeholders - they're the
    real IOG-42 gate, wired in ahead of the feature that doesn't exist
    yet, so nobody can build IOG-40 without going through them.
    """
    require_student_access(actor, student_id)
    ensure_consent_active(session, student_id)
    raise NotImplementedError(
        "Phase 4 (IOG-40) hasn't started. See this module's docstring for scope."
    )

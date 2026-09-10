"""IOG-52: opt-in AI insight for the student dashboard (Deliver layer).

The natural-language counterpart to `get_student_dashboard`: when a hosted
LLM is configured (`src.model.ai_analysis.is_ai_enabled`), it runs the
`SYSTEM_PROMPT` analysis for one student and returns the parsed
`DiagnosticResult` as plain dicts for the template. When no provider is
configured - the default for pytest, a fresh clone, and the current Render
deploy - it returns `enabled=False` and the page shows the local TF-IDF
dashboard as the source of truth instead. The explainable engine stays the
default; this is an enrichment, never a replacement.

Framework-free like `dashboard_api`: takes a Session + Actor, returns plain
dicts. Same IOG-42 gate as every other student view - `require_student_access`
(N6) and `ensure_consent_active` (N2) run before any of the student's rows are
read - and the analysis run is written to the audit log (N4).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.db.models import Student
from src.model.ai_analysis import (
    AIAnalysisError,
    AIAnalysisUnavailable,
    analyze_student,
    is_ai_enabled,
)
from src.security.audit import log_event
from src.security.authorization import Actor, require_student_access
from src.security.consent import ensure_consent_active


def get_ai_insight(session: Session, actor: Actor, student_id: int) -> dict:
    """Return the AI insight view-model for one student.

    Shape: {
      "student": {"id", "display_name"},
      "enabled": bool,          # whether a supported LLM provider is configured
      "insight": dict | None,   # the DiagnosticResult (learningOutcomes, ...)
      "error": str | None,      # set if the provider was called but failed
    }
    """
    # N6 / N2: same gate as the rest of the Deliver layer, before any read.
    require_student_access(actor, student_id)
    ensure_consent_active(session, student_id)

    student = session.get(Student, student_id)
    if student is None:
        raise ValueError(f"No student with id={student_id}")

    base = {
        "student": {"id": student.id, "display_name": student.display_name},
        "enabled": is_ai_enabled(),
        "insight": None,
        "error": None,
    }

    if not base["enabled"]:
        return base

    try:
        result = analyze_student(session, student)
    except AIAnalysisUnavailable:
        # Provider went away between the is_ai_enabled() check and the call.
        base["enabled"] = False
        return base
    except AIAnalysisError as exc:
        base["error"] = str(exc)
        log_event(
            session,
            actor=actor.role.value,
            action="ai_insight_failed",
            target=f"student:{student_id}",
        )
        return base

    base["insight"] = result.model_dump()
    # N4: creating an AI study insight is a study-plan/quiz-class action.
    log_event(
        session,
        actor=actor.role.value,
        action="ai_insight_generated",
        target=f"student:{student_id}",
    )
    return base

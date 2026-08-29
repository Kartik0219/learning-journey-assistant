"""App-build phase database feature: a Staff/Admin-facing coordinator
report - the aggregate, cohort-level counterpart to the existing
per-student dashboard (src.deliver.dashboard_api), answering "how is the
cohort doing" rather than "how is this one student doing".

Built the same way the rest of Estimate/Deliver already reads data: no
recomputation here, only aggregation over what the Model/Estimate stages
already wrote (SkillGap, MasteryScore) via ordinary SQLAlchemy queries -
no new query language, no raw SQL, consistent with N7's shared-DB /
SQLAlchemy choice this feature was explicitly asked to keep.

Same two compliance gates as the per-student dashboard, applied at the
aggregate level instead of the individual level:
  - N6 (authorization): only Staff/Admin may call this at all - a Student
    actor gets AuthorizationError, the same error type/shape
    require_student_access already raises, so callers (src.deliver.app)
    handle it identically.
  - N2 (consent): a student without active consent contributes to no
    aggregate here, the same as they're skipped entirely in
    src.pipeline.run_estimate_stage - "stop further processing", not
    "hide it after the fact", applies to reporting as much as scoring.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from src.db.models import LearningOutcome, MasteryScore, SkillGap, Student, Subject
from src.security.authorization import Actor, AuthorizationError, Role
from src.security.consent import ConsentError, ensure_consent_active

# Below this average mastery across their scored outcomes, a student is
# surfaced on the "at risk" list - named constant so a marker or teammate
# can see exactly where the line is drawn, same convention as
# src.estimate.mastery.SEVERITY_WEIGHT.
AT_RISK_MASTERY_THRESHOLD = 0.5


def _consented_students(session: Session) -> list[Student]:
    students = []
    for student in session.query(Student).all():
        try:
            ensure_consent_active(session, student.id)
        except ConsentError:
            continue
        students.append(student)
    return students


def get_coordinator_report(session: Session, actor: Actor) -> dict:
    """N6: Staff/Admin only - a cohort-level SILO mastery/gap-severity
    breakdown per subject, plus a list of consented students below
    AT_RISK_MASTERY_THRESHOLD. Every average is computed from consented
    students only (N2); a student who has withdrawn or never given
    consent contributes to no number here."""
    if actor.role == Role.STUDENT:
        raise AuthorizationError(
            "Only Staff/Admin may view the coordinator report - a Student "
            "actor has no cohort-level view (N6)."
        )

    students = _consented_students(session)
    student_ids = {s.id for s in students}

    subjects: list[dict] = []
    for subject in session.query(Subject).order_by(Subject.code).all():
        outcomes_report = []
        for lo in (
            session.query(LearningOutcome)
            .filter_by(subject_id=subject.id)
            .order_by(LearningOutcome.code)
            .all()
        ):
            scores = [
                m.score
                for m in session.query(MasteryScore).filter_by(learning_outcome_id=lo.id).all()
                if m.student_id in student_ids
            ]
            avg_mastery = sum(scores) / len(scores) if scores else None

            severity_counts: dict[str, int] = defaultdict(int)
            for gap in (
                session.query(SkillGap)
                .filter_by(learning_outcome_id=lo.id, reviewed=True)
                .all()
            ):
                if gap.assessment_result.student_id not in student_ids:
                    continue
                severity_counts[gap.severity] += 1

            outcomes_report.append(
                {
                    "id": lo.id,
                    "code": lo.code,
                    "description": lo.description,
                    "student_count": len(scores),
                    "average_mastery_pct": (
                        round(avg_mastery * 100) if avg_mastery is not None else None
                    ),
                    "gap_counts": {
                        "high": severity_counts.get("high", 0),
                        "medium": severity_counts.get("medium", 0),
                        "low": severity_counts.get("low", 0),
                    },
                }
            )
        subjects.append(
            {
                "id": subject.id,
                "code": subject.code,
                "name": subject.name,
                "outcomes": outcomes_report,
            }
        )

    at_risk_students = []
    for student in students:
        scores = [
            m.score
            for m in session.query(MasteryScore).filter_by(student_id=student.id).all()
        ]
        if not scores:
            continue
        average = sum(scores) / len(scores)
        if average < AT_RISK_MASTERY_THRESHOLD:
            at_risk_students.append(
                {
                    "id": student.id,
                    "display_name": student.display_name,
                    "average_mastery_pct": round(average * 100),
                }
            )
    at_risk_students.sort(key=lambda s: s["average_mastery_pct"])

    return {
        "subjects": subjects,
        "at_risk_students": at_risk_students,
        "consented_student_count": len(students),
    }

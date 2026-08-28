"""Phase 4 (IOG-40): student-facing dashboard data (F10).

Owns assembling the per-student view: mastery by learning outcome,
priority topics, recommended study material, and the evidence behind
each - scoped to the logged-in student only (N6 - "one student cannot
open another student's records").

This module is deliberately framework-free: it takes a Session and an
Actor and returns plain dicts, so it can be unit-tested without Flask
and reused if the team ever swaps the web layer. src.deliver.app is the
Flask route that calls this and renders it.

IOG-42 (Phase 5) contract this follows: `require_student_access` and
`ensure_consent_active` (src.security) run *before* touching any of
this student's rows - both already raise the right error type on their
own, there is no need to catch and re-wrap them here.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.db.models import LearningOutcome, MasteryScore, Student, StudyRecommendation
from src.security.authorization import Actor, require_student_access
from src.security.consent import ensure_consent_active


def _latest_recommendation(
    session: Session, student_id: int, learning_outcome_id: int
) -> StudyRecommendation | None:
    return (
        session.query(StudyRecommendation)
        .filter_by(student_id=student_id, learning_outcome_id=learning_outcome_id)
        .order_by(StudyRecommendation.created_at.desc())
        .first()
    )


def get_student_dashboard(session: Session, actor: Actor, student_id: int) -> dict:
    """F10: assemble mastery, priority topics, and recommended study
    material for one student. Read-only - it reads whatever the Estimate
    stage (src.estimate.mastery) already computed and written to the
    database; it does not recompute scores on every page view.
    """
    require_student_access(actor, student_id)
    ensure_consent_active(session, student_id)

    student = session.get(Student, student_id)
    if student is None:
        raise ValueError(f"No student with id={student_id}")

    outcomes: list[dict] = []
    for lo in session.query(LearningOutcome).order_by(LearningOutcome.code).all():
        mastery = (
            session.query(MasteryScore)
            .filter_by(student_id=student_id, learning_outcome_id=lo.id)
            .one_or_none()
        )
        # F4: only ever surface *reviewed* gaps to the student - anything
        # below the confidence threshold stays hidden until a human
        # checks it, however low that mastery score might otherwise look.
        gaps = [
            {
                "evidence": gap.source_evidence_text,
                "severity": gap.severity,
                "confidence": gap.confidence,
            }
            for result in student.results
            for gap in result.skill_gaps
            if gap.learning_outcome_id == lo.id and gap.reviewed
        ]

        recommendation = _latest_recommendation(session, student_id, lo.id)

        outcomes.append(
            {
                "id": lo.id,
                "code": lo.code,
                "description": lo.description,
                "mastery_score": mastery.score if mastery else None,
                "mastery_pct": round(mastery.score * 100) if mastery else None,
                "explanation": mastery.explanation_text if mastery else None,
                "gaps": gaps,
                "recommendation": (
                    {
                        "id": recommendation.id,
                        "method": recommendation.method,
                        "material_text": recommendation.material_text,
                        "source_title": (
                            recommendation.source_topic_material.title
                            if recommendation.source_topic_material
                            else None
                        ),
                    }
                    if recommendation
                    else None
                ),
            }
        )

    priority_outcomes = sorted(
        (o for o in outcomes if o["mastery_score"] is not None),
        key=lambda o: o["mastery_score"],
    )[:3]

    return {
        "student": {"id": student.id, "display_name": student.display_name},
        "outcomes": outcomes,
        "priority_outcomes": priority_outcomes,
    }

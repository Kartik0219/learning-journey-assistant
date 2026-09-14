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

import re

from sqlalchemy.orm import Session

from src.connect.excel_loader import parse_silo_tags
from src.db.models import LearningOutcome, MasteryScore, Student, StudyRecommendation, TopicMaterial
from src.estimate.quiz import latest_quiz_questions
from src.security.authorization import Actor, require_student_access
from src.security.consent import ensure_consent_active

_SILO_NUMBER = re.compile(r"SILO(\d+)", re.IGNORECASE)

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
        # App-build phase AI feature (F8): quiz questions Estimate already
        # generated for this outcome, read back the same way a study
        # recommendation is - not regenerated on every page view.
        quiz_questions = [
            {
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                # The grounded "model answer" for the interactive quiz: the
                # source TopicMaterial passage this question was built from
                # (F8/F9 grounding), surfaced separately so the quiz UI can
                # reveal it after the student attempts their own answer.
                "answer_title": (
                    q.source_topic_material.title if q.source_topic_material else None
                ),
                "answer_text": (
                    q.source_topic_material.passage_text if q.source_topic_material else None
                ),
                "answer_url": (
                    q.source_topic_material.source_url if q.source_topic_material else None
                ),
            }
            for q in latest_quiz_questions(session, student_id, lo.id)
        ]

        outcomes.append(
            {
                "id": lo.id,
                "code": lo.code,
                "description": lo.description,
                "subject_code": lo.subject.code,
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
                        "source_url": (
                            recommendation.source_topic_material.source_url
                            if recommendation.source_topic_material
                            else None
                        ),
                        "source_provenance": (
                            recommendation.source_topic_material.provenance
                            if recommendation.source_topic_material
                            else None
                        ),
                    }
                    if recommendation
                    else None
                ),
                "quiz_questions": quiz_questions,
            }
        )

    priority_outcomes = sorted(
        (o for o in outcomes if o["mastery_score"] is not None),
        key=lambda o: o["mastery_score"],
    )[:3]

    # Frontend feature (app-build phase): a per-subject rollup for the
    # dashboard's overview strip - one row per subject the student has at
    # least one scored outcome in, so a multi-subject student (the real
    # dataset's shape) gets an at-a-glance summary before the per-SILO
    # detail below it, rather than only ever seeing a flat outcome list.
    subject_summary: dict[str, list[float]] = {}
    for o in outcomes:
        if o["mastery_score"] is not None:
            subject_summary.setdefault(o["subject_code"], []).append(o["mastery_score"])
    subjects = [
        {"code": code, "average_mastery_pct": round(sum(scores) / len(scores) * 100)}
        for code, scores in subject_summary.items()
    ]

    return {
        "student": {"id": student.id, "display_name": student.display_name},
        "outcomes": outcomes,
        "priority_outcomes": priority_outcomes,
        "subjects": subjects,
    }

def get_student_resources(session: Session, actor: Actor, student_id: int) -> dict:
    """F9: a browsable list of the grounding source materials for this
    student's subjects (mobile nav scope-out's Resources tab) - the same
    TopicMaterial passages recommendations and quizzes are already
    grounded in (F8's "check each generated item against the subject
    materials before it is shown"), surfaced here as a standalone
    reference list rather than only ever attached to one recommendation
    at a time.
    """
    require_student_access(actor, student_id)
    ensure_consent_active(session, student_id)

    student = session.get(Student, student_id)
    if student is None:
        raise ValueError(f"No student with id={student_id}")

    # Same subject-scoping the dashboard's overview strip uses: only
    # subjects this student actually has a scored outcome in. The mastery
    # per outcome is kept so the list can be personalised: resources for
    # the student's weakest SILOs come first, not alphabetical order.
    mastery_rows = session.query(MasteryScore).filter_by(student_id=student_id).all()
    subject_ids = {m.learning_outcome.subject_id for m in mastery_rows}
    mastery_by_outcome = {m.learning_outcome_id: m.score for m in mastery_rows}

    by_subject: dict[str, list[dict]] = {}
    if subject_ids:
        materials = (
            session.query(TopicMaterial)
            .filter(TopicMaterial.subject_id.in_(subject_ids))
            .order_by(TopicMaterial.subject_id, TopicMaterial.title)
            .all()
        )
        for material in materials:
            score = mastery_by_outcome.get(material.learning_outcome_id)
            by_subject.setdefault(material.subject.code, []).append(
                {
                    "title": material.title,
                    "passage_text": material.passage_text,
                    "learning_outcome_code": (
                        material.learning_outcome.code if material.learning_outcome else None
                    ),
                    "learning_outcome_description": (
                        material.learning_outcome.description if material.learning_outcome else None
                    ),
                    "source_url": material.source_url,
                    "provenance": material.provenance,
                    "resource_type": material.resource_type,
                    "mastery_pct": round(score * 100) if score is not None else None,
                }
            )

    def _silo_key(item: dict) -> str:
        return item["learning_outcome_code"] or "General"

    def _natural_silo_order(code: str) -> tuple[int, str]:
        # "SILO1" < "SILO2" < ... < "SILO10" (not "SILO1" < "SILO10" < "SILO2"),
        # "General" (untagged material) always last.
        match = _SILO_NUMBER.match(code)
        return (int(match.group(1)), code) if match else (10_000, code)

    subjects = []
    for code, items in by_subject.items():
        by_silo: dict[str, list[dict]] = {}
        for item in items:
            by_silo.setdefault(_silo_key(item), []).append(item)
        silos = [
            {
                "code": silo_code,
                "description": next((m["learning_outcome_description"] for m in silo_items if m["learning_outcome_description"] is not None), None),
                "mastery_pct": next((m["mastery_pct"] for m in silo_items if m["mastery_pct"] is not None), None),
                "materials": silo_items,
            }
            for silo_code, silo_items in by_silo.items()
        ]
        silos.sort(key=lambda s: _natural_silo_order(s["code"]))
        subjects.append({"code": code, "silos": silos})

    subjects.sort(key=lambda s: s["code"])

    return {
        "student": {"id": student.id, "display_name": student.display_name},
        "subjects": subjects,
    }


def get_student_results(session: Session, actor: Actor, student_id: int) -> dict:
    """Every assessment result for one student, grouped by subject, carrying
    the workbook's own columns (Assessment Type, Score, Feedback Comment,
    SILO's, Weight, Weighted Score) unchanged. Weight and weighted score are
    None for the sample dataset, which has neither column."""
    require_student_access(actor, student_id)
    ensure_consent_active(session, student_id)

    student = session.get(Student, student_id)
    if student is None:
        raise ValueError(f"No student with id={student_id}")

    by_subject: dict[int, dict] = {}
    for result in sorted(student.results, key=lambda r: (r.assessment.subject.code, r.assessment.name)):
        subject = result.assessment.subject
        entry = by_subject.setdefault(
            subject.id, {"code": subject.code, "name": subject.name, "assessments": []}
        )
        entry["assessments"].append(
            {
                "assessment_type": result.assessment.name,
                "score": result.score,
                "feedback": result.feedback_text,
                "silos": parse_silo_tags(result.silo_tags_text or ""),
                "weight": result.weight,
                "weighted_score": result.weighted_score,
            }
        )

    subjects = []
    for entry in by_subject.values():
        weighted = [a["weighted_score"] for a in entry["assessments"] if a["weighted_score"] is not None]
        entry["total_weighted_score"] = round(sum(weighted), 2) if weighted else None
        subjects.append(entry)

    return {
        "student": {"id": student.id, "display_name": student.display_name},
        "subjects": subjects,
    }

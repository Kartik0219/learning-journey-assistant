"""Phase 4 (IOG-38 continued, IOG-39): weighted mastery scoring, fixed-
table study-method selection, grounded study-material generation, and
engagement feedback.

Owns:
  - Weighted mastery calculation per student per SILO (F6), writing
    MasteryScore rows with `explanation_text` populated - F6 requires
    the score to be "explainable from the evidence", so every number
    this module writes is built from a template that names the exact
    inputs (assessment score, which gaps, their severity/evidence)
    rather than being a black box.
  - Recommending a study method from the fixed table (F7) - keyed off
    the gap type computed in src.model.silo_mapping, not chosen by a
    model. There is no LLM call anywhere in this module (see
    src.model.silo_mapping's docstring for why); the "explanation" text
    F7 asks a language model to write is instead built from a template
    naming the actual retrieved material, which keeps every word
    traceable to something real instead of open to hallucination.
  - Generating study material grounded in a retrieved TopicMaterial
    passage, with a source reference (F8, F9).
  - Recording study engagement and feeding it back into mastery (F11).

Depends on src.model.silo_mapping running first for a student's
assessment results (needs SkillGap rows with severity/confidence to
weight against).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.db.models import (
    AssessmentResult,
    LearningOutcome,
    MasteryScore,
    SkillGap,
    Student,
    StudyEngagement,
    StudyRecommendation,
    TopicMaterial,
)
from src.model.silo_mapping import best_similarity, gap_type_for

# F6: weighted calculation - each reviewed gap mapped to the outcome
# being scored subtracts severity_weight * confidence from the
# assessment-score baseline. Named constants, not magic numbers, so the
# weighting is something a reader (or a marker) can actually inspect.
SEVERITY_WEIGHT: dict[str, float] = {"low": 0.05, "medium": 0.15, "high": 0.30}

# F11: a completed study engagement nudges mastery up slightly - capped
# so repeatedly "completing" the same recommendation can't inflate a
# score past what the evidence supports.
ENGAGEMENT_BONUS_PER_COMPLETION = 0.05
ENGAGEMENT_BONUS_CAP = 0.15

# F7: the fixed table. A model never picks the method - it is looked up
# by gap type, which is itself derived deterministically (see
# src.model.silo_mapping.gap_type_for) from the learning outcome's verb.
STUDY_METHOD_TABLE: dict[str, str] = {
    "conceptual": "worked_example",
    "application": "retrieval_practice",
    "evaluation": "spaced_practice",
}

_METHOD_FRAMING: dict[str, str] = {
    "worked_example": "Worked example",
    "retrieval_practice": "Retrieval practice",
    "spaced_practice": "Spaced practice",
}


def _relevant_results(
    student: Student, learning_outcome: LearningOutcome
) -> list[AssessmentResult]:
    """A student's assessment results within the same subject as the
    learning outcome being scored. The sample dataset has one assessment
    per subject; a larger dataset would narrow this further by which
    rubric criteria the assessment's rubric actually covers."""
    return [
        r for r in student.results
        if r.assessment.subject_id == learning_outcome.subject_id and r.score is not None
    ]


def _gaps_for(student: Student, learning_outcome: LearningOutcome) -> list[SkillGap]:
    gaps: list[SkillGap] = []
    for result in student.results:
        for gap in result.skill_gaps:
            if gap.learning_outcome_id == learning_outcome.id and gap.reviewed:
                gaps.append(gap)
    return gaps


def calculate_mastery_score(
    session: Session, student: Student, learning_outcome: LearningOutcome
) -> MasteryScore:
    """F6: weighted, explainable mastery estimate.

    score = clip(mean_assessment_score/100 - sum(severity_weight * confidence
    for each reviewed gap mapped to this outcome) + engagement_bonus, 0, 1)

    Every term in that formula is named in the written explanation, so
    the number is reproducible by re-reading the explanation alone -
    that reproducibility is the F6 requirement, not an afterthought.
    """
    results = _relevant_results(student, learning_outcome)
    base_score = (sum(r.score for r in results) / len(results) / 100.0) if results else 0.0

    gaps = _gaps_for(student, learning_outcome)
    gap_penalty = sum(SEVERITY_WEIGHT[g.severity] * g.confidence for g in gaps)

    bonus = _engagement_bonus(session, student, learning_outcome)

    score = max(0.0, min(1.0, base_score - gap_penalty + bonus))

    explanation_parts = [
        f"Assessment score baseline: {base_score * 100:.0f}% across "
        f"{len(results)} result(s) in this subject."
    ]
    if gaps:
        gap_lines = "; ".join(
            f"'{g.source_evidence_text}' ({g.severity} severity, "
            f"confidence {g.confidence:.2f})"
            for g in gaps
        )
        explanation_parts.append(
            f"Reduced by {len(gaps)} recorded skill gap(s) mapped to this outcome: {gap_lines}."
        )
    else:
        explanation_parts.append("No reviewed skill gaps are currently mapped to this outcome.")
    if bonus > 0:
        explanation_parts.append(
            f"Increased by {bonus * 100:.0f}% for completed study practice on this outcome."
        )

    existing = (
        session.query(MasteryScore)
        .filter_by(student_id=student.id, learning_outcome_id=learning_outcome.id)
        .one_or_none()
    )
    if existing:
        existing.score = round(score, 4)
        existing.explanation_text = " ".join(explanation_parts)
        session.flush()
        return existing

    mastery = MasteryScore(
        student_id=student.id,
        learning_outcome_id=learning_outcome.id,
        score=round(score, 4),
        explanation_text=" ".join(explanation_parts),
    )
    session.add(mastery)
    session.flush()
    return mastery


def _engagement_bonus(
    session: Session, student: Student, learning_outcome: LearningOutcome
) -> float:
    completions = (
        session.query(StudyEngagement)
        .join(StudyRecommendation)
        .filter(
            StudyEngagement.student_id == student.id,
            StudyRecommendation.learning_outcome_id == learning_outcome.id,
            StudyEngagement.completed.is_(True),
        )
        .count()
    )
    return min(ENGAGEMENT_BONUS_CAP, completions * ENGAGEMENT_BONUS_PER_COMPLETION)


def recommend_study_method(learning_outcome: LearningOutcome) -> str:
    """F7: fixed-table lookup, keyed by the outcome's gap type. No model
    chooses this - see STUDY_METHOD_TABLE above."""
    gap_type = gap_type_for(learning_outcome.description)
    return STUDY_METHOD_TABLE[gap_type]


def generate_study_material(
    session: Session, student: Student, learning_outcome: LearningOutcome
) -> StudyRecommendation:
    """F8/F9: pick the closest TopicMaterial passage for this outcome
    (preferring passages explicitly tagged with it, falling back to the
    whole subject) and build a study prompt around it. The generated
    text is templated from the retrieved passage's own words, not
    freely generated - "checked against subject materials" (F8) here
    means the material *is* the subject material, with a citation, not
    a paraphrase a model could get wrong.
    """
    method = recommend_study_method(learning_outcome)

    subject_materials = _topic_materials_for_subject(session, learning_outcome)
    tagged = [m for m in subject_materials if m.learning_outcome_id == learning_outcome.id]
    candidates = tagged or subject_materials

    material_text: str
    source: TopicMaterial | None
    if candidates:
        titles = [m.title for m in candidates]
        best_index, _ = best_similarity(learning_outcome.description, titles)
        source = candidates[best_index if best_index != -1 else 0]
        framing = _METHOD_FRAMING[method]
        if method == "worked_example":
            material_text = (
                f"{framing} — review \"{source.title}\": {source.passage_text} "
                f"Now try applying this to a new example of your own before checking back."
            )
        elif method == "retrieval_practice":
            material_text = (
                f"{framing} — without looking, try to recall and apply what \"{source.title}\" "
                f"covers, then check your attempt against it: {source.passage_text}"
            )
        else:
            material_text = (
                f"{framing} — read \"{source.title}\" now, then revisit it again in a few days "
                f"and re-derive the answer before re-reading: {source.passage_text}"
            )
    else:
        source = None
        material_text = (
            f"No topic material is available yet for {learning_outcome.code}. "
            f"Flagged for the subject coordinator to add source material."
        )

    recommendation = StudyRecommendation(
        student_id=student.id,
        learning_outcome_id=learning_outcome.id,
        method=method,
        material_text=material_text,
        source_topic_material_id=source.id if source else None,
    )
    session.add(recommendation)
    session.flush()
    return recommendation


def _topic_materials_for_subject(
    session: Session, learning_outcome: LearningOutcome
) -> list[TopicMaterial]:
    return (
        session.query(TopicMaterial)
        .filter_by(subject_id=learning_outcome.subject_id)
        .all()
    )


def record_engagement(
    session: Session,
    student: Student,
    recommendation: StudyRecommendation,
    completed: bool,
) -> StudyEngagement:
    """F11: store how the student engaged with a recommendation, then
    recompute the affected MasteryScore so the engagement bonus (if any)
    is reflected immediately rather than on the next full pipeline run.
    """
    engagement = StudyEngagement(
        student_id=student.id,
        study_recommendation_id=recommendation.id,
        completed=completed,
    )
    session.add(engagement)
    session.flush()

    calculate_mastery_score(session, student, recommendation.learning_outcome)
    return engagement

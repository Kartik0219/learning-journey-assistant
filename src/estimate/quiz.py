"""App-build phase AI feature: TF-IDF-grounded practice-quiz generation
(F8 - the tender's "generate a practice quiz ... from skill gaps and
topic materials" item, which docs/ENVIRONMENT_SETUP.md's implementation-
status table had flagged as "not yet built").

Deliberately built the same way `src.estimate.mastery.generate_study_
material` already grounds its material - by retrieval, not generation:
every question is templated from (a) a specific reviewed `SkillGap`'s own
verbatim evidence quote and (b) the closest `TopicMaterial` passage found
via `src.model.silo_mapping.best_similarity` (TF-IDF cosine similarity,
scikit-learn, fully local). There is no LLM call anywhere in this module,
for the same reasons `src.model.silo_mapping`'s module docstring gives:
no procurement dependency, and every word in a generated question traces
back to something real rather than being open to hallucination.

Depends on Model (src.model.silo_mapping) having already produced
reviewed SkillGap rows for the student, and (optionally) on Estimate's
own generate_study_material having populated topic-material grounding -
a question can still be produced with no topic material available, same
honest "flagged for the subject coordinator" fallback pattern as F8/F9.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.db.models import LearningOutcome, QuizQuestion, SkillGap, Student, TopicMaterial
from src.model.silo_mapping import best_similarity, gap_type_for

# F8: question framing keyed off the same gap-type classification F7 uses
# to pick a study method - one deterministic mapping, not a model's
# judgment call, so the *kind* of question asked is explainable the same
# way the study method recommended for it already is.
_QUESTION_TYPE_FOR_GAP_TYPE: dict[str, str] = {
    "conceptual": "recall",
    "application": "apply",
    "evaluation": "evaluate",
}

_QUESTION_FRAMING: dict[str, str] = {
    "recall": "In your own words, explain the idea behind",
    "apply": "Work through a new example that applies",
    "evaluate": "Critically evaluate a trade-off involved in",
}


def _reviewed_gaps_for(student: Student, learning_outcome: LearningOutcome) -> list[SkillGap]:
    return [
        gap
        for result in student.results
        for gap in result.skill_gaps
        # F4: only ever build a question from a *reviewed* gap - the same
        # rule the dashboard already enforces for showing a gap at all.
        if gap.learning_outcome_id == learning_outcome.id and gap.reviewed
    ]


def _topic_materials_for_subject(
    session: Session, learning_outcome: LearningOutcome
) -> list[TopicMaterial]:
    return (
        session.query(TopicMaterial).filter_by(subject_id=learning_outcome.subject_id).all()
    )


def _closest_material(
    session: Session, learning_outcome: LearningOutcome, evidence_text: str
) -> TopicMaterial | None:
    subject_materials = _topic_materials_for_subject(session, learning_outcome)
    tagged = [m for m in subject_materials if m.learning_outcome_id == learning_outcome.id]
    candidates = tagged or subject_materials
    if not candidates:
        return None
    titles = [m.title for m in candidates]
    best_index, _ = best_similarity(evidence_text, titles)
    return candidates[best_index if best_index != -1 else 0]


def _build_question_text(
    question_type: str,
    learning_outcome: LearningOutcome,
    gap: SkillGap,
    material: TopicMaterial | None,
) -> str:
    framing = _QUESTION_FRAMING[question_type]
    prompt = f'{framing} "{learning_outcome.code}: {learning_outcome.description}". '
    prompt += f'This was flagged from: "{gap.source_evidence_text}". '
    if material is not None:
        prompt += f'Ground your answer in "{material.title}": {material.passage_text}'
    else:
        prompt += (
            "No topic material is available yet for this outcome - flagged for the "
            "subject coordinator to add source material."
        )
    return prompt


def generate_quiz_questions(
    session: Session,
    student: Student,
    learning_outcome: LearningOutcome,
    max_questions: int = 3,
) -> list[QuizQuestion]:
    """F8: build up to `max_questions` grounded practice questions for one
    student/outcome, one per reviewed skill gap mapped to it (gaps beyond
    `max_questions` are simply not turned into a question this run - there
    is no ranking beyond "which gaps exist", since severity/confidence
    already gate which gaps are reviewed at all).

    Returns an empty list if the student has no reviewed gaps for this
    outcome - a mastered outcome earns no quiz, same as it earns no study
    recommendation pressure.
    """
    gaps = _reviewed_gaps_for(student, learning_outcome)[:max_questions]

    questions: list[QuizQuestion] = []
    for gap in gaps:
        gap_type = gap_type_for(learning_outcome.description)
        question_type = _QUESTION_TYPE_FOR_GAP_TYPE[gap_type]
        material = _closest_material(session, learning_outcome, gap.source_evidence_text)

        question = QuizQuestion(
            student_id=student.id,
            learning_outcome_id=learning_outcome.id,
            source_skill_gap_id=gap.id,
            source_topic_material_id=material.id if material else None,
            question_text=_build_question_text(question_type, learning_outcome, gap, material),
            question_type=question_type,
        )
        session.add(question)
        questions.append(question)

    if questions:
        session.flush()
    return questions


def latest_quiz_questions(
    session: Session, student_id: int, learning_outcome_id: int, limit: int = 3
) -> list[QuizQuestion]:
    """The most recently generated questions for a student/outcome, for
    display - mirrors src.estimate.mastery._latest_recommendation's
    "read back what Estimate already computed" pattern rather than
    regenerating on every page view."""
    return (
        session.query(QuizQuestion)
        .filter_by(student_id=student_id, learning_outcome_id=learning_outcome_id)
        .order_by(QuizQuestion.created_at.desc())
        .limit(limit)
        .all()
    )

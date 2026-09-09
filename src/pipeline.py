"""End-to-end pipeline: Connect -> Parse -> Model -> Estimate, in one
runnable command, against whatever dataset src.connect currently points
at (the bundled sample data, until a real dataset is provided per N9).

    python -m src.pipeline

Deliver (the dashboard) is a separate process - run it with:

    python -m src.deliver.app

so the pipeline can be re-run any time to refresh scores without
restarting the web server.
"""

from __future__ import annotations

from src.common.logging_config import configure_logging, get_logger
from src.db.database import get_session
from src.db.models import AssessmentResult, LearningOutcome, Student
from src.estimate.mastery import calculate_mastery_score, generate_study_material
from src.estimate.quiz import generate_quiz_questions
from src.model.silo_mapping import extract_skill_gaps, map_gap_to_learning_outcome
from src.parse.cleaners import run_parse_stage
from src.security.consent import ConsentError, ensure_consent_active

logger = get_logger(__name__)


def run_model_stage(session) -> tuple[int, int]:
    """Phase 3: extract skill gaps from every assessment result that
    doesn't have any yet, and map each new gap to a learning outcome."""
    gaps_extracted = 0
    gaps_mapped = 0
    for result in session.query(AssessmentResult).all():
        if result.skill_gaps:
            continue  # already processed by an earlier pipeline run
        for gap in extract_skill_gaps(session, result):
            gaps_extracted += 1
            if map_gap_to_learning_outcome(session, gap) is not None:
                gaps_mapped += 1
    return gaps_extracted, gaps_mapped


def run_estimate_stage(session) -> tuple[int, int, int]:
    """Phase 4: (re)calculate mastery and generate a fresh study
    recommendation for every student x learning outcome with active
    consent. N2: students without active consent are skipped entirely,
    not just hidden later - ensure_consent_active is the actual gate."""
    scores_written = 0
    recommendations_written = 0
    questions_written = 0
    outcomes = session.query(LearningOutcome).all()
    for student in session.query(Student).all():
        try:
            ensure_consent_active(session, student.id)
        except ConsentError:
            logger.info("Skipping student id=%s: no active consent.", student.id)
            continue
        for lo in outcomes:
            calculate_mastery_score(session, student, lo)
            scores_written += 1
            generate_study_material(session, student, lo)
            recommendations_written += 1
            # App-build phase AI feature (F8): grounded practice questions,
            # a no-op (empty list) for an outcome with no reviewed gaps.
            questions_written += len(generate_quiz_questions(session, student, lo))
    return scores_written, recommendations_written, questions_written


def run_pipeline() -> None:
    configure_logging()

    run_parse_stage()

    with get_session() as session:
        gaps_extracted, gaps_mapped = run_model_stage(session)
        logger.info(
            "Model stage complete: %d skill gap(s) extracted, %d mapped to a learning outcome.",
            gaps_extracted,
            gaps_mapped,
        )

    with get_session() as session:
        scores_written, recommendations_written, questions_written = run_estimate_stage(session)
        logger.info(
            "Estimate stage complete: %d mastery score(s), %d study recommendation(s), "
            "%d quiz question(s).",
            scores_written,
            recommendations_written,
            questions_written,
        )

    logger.info("Pipeline complete. Run `python -m src.deliver.app` to view the dashboard.")


if __name__ == "__main__":
    run_pipeline()

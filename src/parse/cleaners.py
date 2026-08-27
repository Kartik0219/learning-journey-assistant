"""Cleaning, identifier matching, and load-into-DB orchestration (F2).

F2: "Clean and check incoming records, match student and subject
identifiers, and keep only the fields needed later in the pipeline."

`run_parse_stage()` is the join point between Connect (loads raw rows)
and the shared database: it validates every row through
src.parse.schema_validation, drops rows that fail validation (logging
why), and upserts the rest. This is what makes Phase 1 an actual,
runnable pipeline rather than just schema + folders - run it with:

    python -m src.parse.cleaners

against the bundled sample data.
"""

from __future__ import annotations

import pandas as pd
from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.common.logging_config import configure_logging, get_logger
from src.connect import historical_dataset_loader as loader
from src.db.database import get_session, init_db
from src.db.models import LearningOutcome, Rubric, RubricCriterion, Student, Subject
from src.parse.schema_validation import (
    LearningOutcomeRecord,
    RubricCriterionRecord,
    StudentRecord,
    SubjectRecord,
)
from src.security.audit import log_event
from src.security.encryption import blind_index

logger = get_logger(__name__)


def _validate_rows(df: pd.DataFrame, model: type) -> list:
    """Validate every row of a DataFrame against a Pydantic model.

    Bad rows are logged and dropped rather than raising - one malformed
    row in a large historical dataset shouldn't take down the whole
    import (this is what N5's "reject" means in practice: reject the row,
    not the run).
    """
    valid: list = []
    for i, row in df.iterrows():
        try:
            valid.append(model(**row.dropna().to_dict()))
        except ValidationError as exc:
            logger.warning("Row %s failed validation for %s: %s", i, model.__name__, exc)
    return valid


def upsert_subject(session: Session, record: SubjectRecord) -> Subject:
    existing = session.query(Subject).filter_by(code=record.subject_code).one_or_none()
    if existing:
        existing.name = record.subject_name
        existing.description = record.description
        return existing
    subject = Subject(
        code=record.subject_code, name=record.subject_name, description=record.description
    )
    session.add(subject)
    session.flush()  # get subject.id without a full commit
    return subject


def upsert_learning_outcome(session: Session, record: LearningOutcomeRecord) -> LearningOutcome:
    subject = session.query(Subject).filter_by(code=record.subject_code).one()
    existing = (
        session.query(LearningOutcome)
        .filter_by(subject_id=subject.id, code=record.silo_code)
        .one_or_none()
    )
    if existing:
        existing.description = record.description
        return existing
    outcome = LearningOutcome(
        subject_id=subject.id, code=record.silo_code, description=record.description
    )
    session.add(outcome)
    session.flush()
    return outcome


def upsert_student(session: Session, record: StudentRecord) -> Student:
    # N3: student_number is encrypted at rest (EncryptedString), so it can't
    # be looked up directly - filter on the deterministic blind index
    # instead. See src/security/encryption.py.
    number_hash = blind_index(record.student_number)
    existing = session.query(Student).filter_by(student_number_hash=number_hash).one_or_none()
    if existing:
        existing.display_name = record.display_name
        return existing
    # student_number_hash is set automatically by Student's validator.
    student = Student(student_number=record.student_number, display_name=record.display_name)
    session.add(student)
    session.flush()
    return student


def upsert_rubric_criterion(session: Session, record: RubricCriterionRecord) -> RubricCriterion:
    subject = session.query(Subject).filter_by(code=record.subject_code).one()
    rubric = (
        session.query(Rubric)
        .filter_by(subject_id=subject.id, name=record.rubric_name)
        .one_or_none()
    )
    if rubric is None:
        rubric = Rubric(subject_id=subject.id, name=record.rubric_name)
        session.add(rubric)
        session.flush()

    learning_outcome_id = None
    if record.silo_code:
        outcome = (
            session.query(LearningOutcome)
            .filter_by(subject_id=subject.id, code=record.silo_code)
            .one_or_none()
        )
        learning_outcome_id = outcome.id if outcome else None

    criterion = RubricCriterion(
        rubric_id=rubric.id,
        learning_outcome_id=learning_outcome_id,
        criterion_text=record.criterion_text,
    )
    session.add(criterion)
    return criterion


def run_parse_stage() -> None:
    """End-to-end: load sample/historical data, validate, load into DB."""
    configure_logging()
    init_db()

    subjects = _validate_rows(loader.load_subjects(), SubjectRecord)
    learning_outcomes = _validate_rows(loader.load_learning_outcomes(), LearningOutcomeRecord)
    rubric_criteria = _validate_rows(loader.load_rubrics(), RubricCriterionRecord)
    students = _validate_rows(loader.load_students(), StudentRecord)

    with get_session() as session:
        for record in subjects:
            upsert_subject(session, record)
        for record in learning_outcomes:
            upsert_learning_outcome(session, record)
        for record in rubric_criteria:
            upsert_rubric_criterion(session, record)
        for record in students:
            upsert_student(session, record)

        # N4: audit log must record every data import.
        log_event(
            session,
            actor="system",
            action="data_import",
            target=(
                f"{len(subjects)} subjects, {len(learning_outcomes)} learning outcomes, "
                f"{len(rubric_criteria)} rubric criteria, {len(students)} students"
            ),
        )

    logger.info(
        "Parse stage complete: %d subjects, %d learning outcomes, %d rubric criteria, %d students",
        len(subjects),
        len(learning_outcomes),
        len(rubric_criteria),
        len(students),
    )


if __name__ == "__main__":
    run_parse_stage()

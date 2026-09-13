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
from src.config import get_settings
from src.connect import excel_loader, historical_dataset_loader
from src.db.database import get_session, init_db
from src.db.models import (
    Assessment,
    AssessmentResult,
    LearningOutcome,
    Rubric,
    RubricCriterion,
    Student,
    Subject,
    TopicMaterial,
    UserCredential,
)
from src.parse.schema_validation import (
    AssessmentResultRecord,
    LearningOutcomeRecord,
    RubricCriterionRecord,
    StudentRecord,
    SubjectRecord,
    TopicMaterialRecord,
)
from src.security.audit import log_event
from src.security.authentication import set_staff_password, set_student_password
from src.security.authorization import Role
from src.security.consent import record_consent
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


def upsert_assessment_result(session: Session, record: AssessmentResultRecord) -> AssessmentResult:
    """F1/F2: load the grade + written feedback that Phase 3 extracts
    skill gaps from. Creates the parent Assessment row on first sight of
    an (subject, assessment_name) pair, then upserts the per-student
    result under it."""
    subject = session.query(Subject).filter_by(code=record.subject_code).one()
    assessment = (
        session.query(Assessment)
        .filter_by(subject_id=subject.id, name=record.assessment_name)
        .one_or_none()
    )
    if assessment is None:
        assessment = Assessment(subject_id=subject.id, name=record.assessment_name)
        session.add(assessment)
        session.flush()

    student_hash = blind_index(record.student_number)
    student = session.query(Student).filter_by(student_number_hash=student_hash).one()

    existing = (
        session.query(AssessmentResult)
        .filter_by(assessment_id=assessment.id, student_id=student.id)
        .one_or_none()
    )
    if existing:
        existing.score = record.score
        existing.feedback_text = record.feedback_text
        # IOG-33: carry the real dataset's explicit SILO tags through on
        # re-import too, not just on first insert.
        existing.silo_tags_text = record.silo_tags_text
        existing.weight = record.weight
        existing.weighted_score = record.weighted_score
        return existing

    result = AssessmentResult(
        assessment_id=assessment.id,
        student_id=student.id,
        score=record.score,
        feedback_text=record.feedback_text,
        silo_tags_text=record.silo_tags_text,
        weight=record.weight,
        weighted_score=record.weighted_score,
    )
    session.add(result)
    session.flush()
    return result


def upsert_topic_material(session: Session, record: TopicMaterialRecord) -> TopicMaterial:
    """F9: load a subject topic-material passage. Idempotent on
    (subject, title) so re-running the pipeline doesn't duplicate rows."""
    subject = session.query(Subject).filter_by(code=record.subject_code).one()

    learning_outcome_id = None
    if record.silo_code:
        outcome = (
            session.query(LearningOutcome)
            .filter_by(subject_id=subject.id, code=record.silo_code)
            .one_or_none()
        )
        learning_outcome_id = outcome.id if outcome else None

    existing = (
        session.query(TopicMaterial)
        .filter_by(subject_id=subject.id, title=record.title)
        .one_or_none()
    )
    if existing:
        existing.learning_outcome_id = learning_outcome_id
        existing.passage_text = record.passage_text
        return existing

    material = TopicMaterial(
        subject_id=subject.id,
        learning_outcome_id=learning_outcome_id,
        title=record.title,
        passage_text=record.passage_text,
    )
    session.add(material)
    return material


def seed_demo_consent(session: Session, students: list[Student]) -> int:
    """N2/F2 demo-data note: the bundled sample dataset represents already-
    consented demo students (there is no real consent-collection UI yet -
    that depends on Phase 4/6's login system, IOG-40). Consent is still
    recorded through the real `record_consent()` API - same code path a
    genuine consent flow would use, same audit-log entry written - rather
    than bypassed. This only runs for students that don't already have a
    consent record, so it's safe to call on every pipeline run.
    """
    seeded = 0
    for student in students:
        if student.consent is not None:
            continue
        record_consent(session, student, given=True)
        seeded += 1
    return seeded


def seed_demo_credentials(session: Session, students: list[Student]) -> int:
    """App-build phase (N1): seed a real, hashed sign-in credential for
    every student that doesn't already have one, plus one fixed Staff and
    one fixed Admin demo account.

    The demo password for a student is their own student number (e.g.
    student DEMO0001 signs in with student number "DEMO0001" and password
    "DEMO0001") - fixed and documented (see docs/ENVIRONMENT_SETUP.md),
    the same demonstration-scope disclosure the old picker-based login
    already made, not a claim of production-grade credential management.
    Staff/Admin demo credentials are "staff"/"staff123" and
    "admin"/"admin123" respectively. Idempotent like seed_demo_consent -
    safe to call on every pipeline run.
    """
    seeded = 0
    for student in students:
        already_has_credential = (
            session.query(UserCredential).filter_by(student_id=student.id).one_or_none()
        )
        if already_has_credential:
            continue
        set_student_password(session, student, student.student_number)
        seeded += 1

    if not session.query(UserCredential).filter_by(username="staff").one_or_none():
        set_staff_password(session, "staff", Role.STAFF, "staff123")
        seeded += 1
    if not session.query(UserCredential).filter_by(username="admin").one_or_none():
        set_staff_password(session, "admin", Role.ADMIN, "admin123")
        seeded += 1

    return seeded


def _select_loader():
    """IOG-33/N9: pick the real Excel loader when HISTORICAL_DATASET_PATH
    is set, otherwise fall back to the synthetic CSV loader - same
    unset-means-fallback pattern already used for Moodle credentials.
    Kept as one place to switch so nothing else in this module (or its
    tests) needs to know which dataset shape is active."""
    if get_settings().historical_dataset_path:
        return excel_loader
    return historical_dataset_loader


def run_parse_stage() -> None:
    """End-to-end: load sample/historical/real data, validate, load into DB."""
    configure_logging()
    init_db()

    loader = _select_loader()
    logger.info("Parse stage using loader: %s", loader.__name__)

    subjects = _validate_rows(loader.load_subjects(), SubjectRecord)
    learning_outcomes = _validate_rows(loader.load_learning_outcomes(), LearningOutcomeRecord)
    rubric_criteria = _validate_rows(loader.load_rubrics(), RubricCriterionRecord)
    students = _validate_rows(loader.load_students(), StudentRecord)
    assessment_results = _validate_rows(loader.load_assessment_results(), AssessmentResultRecord)
    topic_materials = _validate_rows(loader.load_topic_materials(), TopicMaterialRecord)

    with get_session() as session:
        for record in subjects:
            upsert_subject(session, record)
        for record in learning_outcomes:
            upsert_learning_outcome(session, record)
        for record in rubric_criteria:
            upsert_rubric_criterion(session, record)
        loaded_students = [upsert_student(session, record) for record in students]
        for record in assessment_results:
            upsert_assessment_result(session, record)
        for record in topic_materials:
            upsert_topic_material(session, record)

        consented = seed_demo_consent(session, loaded_students)
        credentials_seeded = seed_demo_credentials(session, loaded_students)

        # N4: audit log must record every data import.
        log_event(
            session,
            actor="system",
            action="data_import",
            target=(
                f"{len(subjects)} subjects, {len(learning_outcomes)} learning outcomes, "
                f"{len(rubric_criteria)} rubric criteria, {len(students)} students, "
                f"{len(assessment_results)} assessment results, "
                f"{len(topic_materials)} topic materials ({consented} consent records seeded, "
                f"{credentials_seeded} sign-in credentials seeded)"
            ),
        )

    logger.info(
        "Parse stage complete: %d subjects, %d learning outcomes, %d rubric criteria, "
        "%d students, %d assessment results, %d topic materials",
        len(subjects),
        len(learning_outcomes),
        len(rubric_criteria),
        len(students),
        len(assessment_results),
        len(topic_materials),
    )


if __name__ == "__main__":
    run_parse_stage()

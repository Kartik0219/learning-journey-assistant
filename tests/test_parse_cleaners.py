"""Integration test: sample CSVs -> validation -> shared DB.

This is the closest thing Phase 1 has to "does the pipeline actually
work end to end" - it's intentionally not mocked, it runs the real
sample data through the real Connect -> Parse -> DB path.
"""

from src.connect import historical_dataset_loader as loader
from src.db.database import get_session
from src.db.models import LearningOutcome, RubricCriterion, Student, Subject
from src.parse.cleaners import (
    upsert_learning_outcome,
    upsert_rubric_criterion,
    upsert_student,
    upsert_subject,
)
from src.parse.schema_validation import (
    LearningOutcomeRecord,
    RubricCriterionRecord,
    StudentRecord,
    SubjectRecord,
)


def test_sample_data_loads_and_validates_cleanly():
    """The bundled sample CSVs should always pass validation - if this
    test fails, someone edited a sample file without keeping it in sync
    with schema_validation.py.
    """
    for record in loader.load_subjects().to_dict("records"):
        SubjectRecord(**record)
    for record in loader.load_learning_outcomes().to_dict("records"):
        LearningOutcomeRecord(**record)
    for record in loader.load_rubrics().to_dict("records"):
        RubricCriterionRecord(**{k: v for k, v in record.items() if v == v})  # drop NaN
    for record in loader.load_students().to_dict("records"):
        StudentRecord(**record)


def test_full_parse_stage_populates_shared_db(clean_db):
    subjects = [SubjectRecord(**r) for r in loader.load_subjects().to_dict("records")]
    outcomes = [
        LearningOutcomeRecord(**r) for r in loader.load_learning_outcomes().to_dict("records")
    ]
    criteria = [
        RubricCriterionRecord(**{k: v for k, v in r.items() if v == v})
        for r in loader.load_rubrics().to_dict("records")
    ]
    students = [StudentRecord(**r) for r in loader.load_students().to_dict("records")]

    with get_session() as session:
        for record in subjects:
            upsert_subject(session, record)
        for record in outcomes:
            upsert_learning_outcome(session, record)
        for record in criteria:
            upsert_rubric_criterion(session, record)
        for record in students:
            upsert_student(session, record)

    with get_session() as session:
        assert session.query(Subject).count() == len(subjects)
        assert session.query(LearningOutcome).count() == len(outcomes)
        assert session.query(RubricCriterion).count() == len(criteria)
        assert session.query(Student).count() == len(students)

        # F5: at least one rubric criterion in the sample data should be
        # linked to a SILO - this is the mapping IOG-34/IOG-38 build on.
        linked = session.query(RubricCriterion).filter(
            RubricCriterion.learning_outcome_id.isnot(None)
        )
        assert linked.count() > 0


def test_student_number_is_normalised_uppercase():
    record = StudentRecord(student_number="  demo9999  ", display_name="Someone")
    assert record.student_number == "DEMO9999"

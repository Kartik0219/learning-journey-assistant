import datetime as dt

from src.db.database import get_session
from src.db.models import ConsentRecord, LearningOutcome, Student, Subject


def test_create_subject_with_learning_outcome(clean_db):
    with get_session() as session:
        subject = Subject(code="DEMO101", name="Demo Subject")
        session.add(subject)
        session.flush()
        outcome = LearningOutcome(subject_id=subject.id, code="SILO1", description="Do the thing.")
        session.add(outcome)

    with get_session() as session:
        stored = session.query(Subject).filter_by(code="DEMO101").one()
        assert stored.name == "Demo Subject"
        assert len(stored.learning_outcomes) == 1
        assert stored.learning_outcomes[0].code == "SILO1"


def test_consent_record_is_active_only_when_given_and_not_withdrawn(clean_db):
    with get_session() as session:
        student = Student(student_number="DEMO0001", display_name="Sample Student")
        session.add(student)
        session.flush()

        no_consent = ConsentRecord(student_id=student.id, consent_given=False)
        assert no_consent.is_active is False

        given = ConsentRecord(
            student_id=student.id,
            consent_given=True,
            consent_date=dt.datetime.now(dt.timezone.utc),
        )
        assert given.is_active is True

        given.withdrawn_date = dt.datetime.now(dt.timezone.utc)
        assert given.is_active is False

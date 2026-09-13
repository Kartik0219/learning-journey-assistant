"""Tests for IOG-42 (Phase 5): encryption, blind-index lookups, consent
gating, authorization, and audit logging."""

import datetime as dt

import pytest
from sqlalchemy import text

from src.db.database import engine, get_session
from src.db.models import AuditLogEntry, ConsentRecord, Student
from src.security.audit import log_event
from src.security.authorization import Actor, AuthorizationError, Role, require_student_access
from src.security.consent import ConsentError, ensure_consent_active, record_consent
from src.security.encryption import blind_index


def test_student_number_round_trips_through_encryption(clean_db):
    """The ORM should decrypt transparently - application code never sees
    ciphertext."""
    with get_session() as session:
        student = Student(student_number="demo1234", display_name="Alex Example")
        session.add(student)
        session.flush()
        student_id = student.id

    with get_session() as session:
        stored = session.get(Student, student_id)
        assert stored.student_number == "demo1234"
        assert stored.display_name == "Alex Example"


def test_student_number_is_encrypted_in_the_raw_database(clean_db):
    """Read the column straight through the DB API (bypassing the ORM's
    decrypting attribute access) to prove ciphertext, not plaintext, is
    what's actually stored on disk."""
    with get_session() as session:
        student = Student(student_number="rawcheck01", display_name="Raw Check")
        session.add(student)
        session.flush()
        student_id = student.id

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT student_number, display_name FROM students WHERE id = :id"),
            {"id": student_id},
        ).one()
        assert "rawcheck01" not in row[0].lower()
        assert "raw check" not in row[1].lower()


def test_blind_index_is_deterministic_and_lookup_works(clean_db):
    """Same input -> same hash every time (needed for lookups); different
    input -> different hash (needed for it to mean anything)."""
    assert blind_index("demo1234") == blind_index("demo1234")
    assert blind_index("demo1234") != blind_index("demo5678")

    with get_session() as session:
        session.add(Student(student_number="lookupme", display_name="Someone"))

    with get_session() as session:
        found = session.query(Student).filter_by(student_number_hash=blind_index("lookupme")).one()
        assert found.display_name == "Someone"


def test_ensure_consent_active_blocks_without_a_consent_record(clean_db):
    with get_session() as session:
        student = Student(student_number="noconsent", display_name="No Consent")
        session.add(student)
        session.flush()
        student_id = student.id

    with get_session() as session:
        with pytest.raises(ConsentError):
            ensure_consent_active(session, student_id)


def test_ensure_consent_active_blocks_after_withdrawal(clean_db):
    with get_session() as session:
        student = Student(student_number="withdrawn1", display_name="Withdrawn")
        session.add(student)
        session.flush()
        session.add(
            ConsentRecord(
                student_id=student.id,
                consent_given=True,
                consent_date=dt.datetime.now(dt.timezone.utc),
                withdrawn_date=dt.datetime.now(dt.timezone.utc),
            )
        )
        student_id = student.id

    with get_session() as session:
        with pytest.raises(ConsentError):
            ensure_consent_active(session, student_id)


def test_record_consent_allows_processing_and_writes_audit_log(clean_db):
    with get_session() as session:
        student = Student(student_number="consented1", display_name="Consented")
        session.add(student)
        session.flush()
        record_consent(session, student, given=True)
        student_id = student.id

    with get_session() as session:
        ensure_consent_active(session, student_id)  # should not raise

        events = session.query(AuditLogEntry).filter_by(action="consent_given").all()
        assert len(events) == 1
        assert events[0].actor == "consented1"


def test_require_student_access_allows_self_only(clean_db):
    require_student_access(Actor(role=Role.STUDENT, student_id=1), target_student_id=1)
    with pytest.raises(AuthorizationError):
        require_student_access(Actor(role=Role.STUDENT, student_id=None), target_student_id=1)


def test_require_student_access_blocks_cross_student_access(clean_db):
    with pytest.raises(AuthorizationError):
        require_student_access(Actor(role=Role.STUDENT, student_id=1), target_student_id=2)


def test_dashboard_stub_enforces_security_before_raising_not_implemented(clean_db):
    """IOG-40 doesn't exist yet, but the IOG-42 gate in front of it must
    already be live - a cross-student request should fail on
    authorization, never reach the NotImplementedError."""
    from src.deliver.dashboard_api import get_student_dashboard

    with get_session() as session:
        with pytest.raises(AuthorizationError):
            get_student_dashboard(session, Actor(role=Role.STUDENT, student_id=1), student_id=2)


def test_log_event_writes_an_audit_row(clean_db):
    with get_session() as session:
        log_event(session, actor="system", action="data_import", target="test batch")

    with get_session() as session:
        entry = session.query(AuditLogEntry).filter_by(action="data_import").one()
        assert entry.target == "test batch"
        assert entry.actor == "system"

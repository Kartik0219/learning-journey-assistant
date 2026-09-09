"""Tests for the app-build phase's real password authentication
(src.security.authentication), which replaces the old demo picker in
src.deliver.app's login route.
"""

from __future__ import annotations

import pytest

from src.db.database import get_session
from src.db.models import Student
from src.security.authentication import (
    AuthenticationError,
    authenticate_staff,
    authenticate_student,
    hash_password,
    set_staff_password,
    set_student_password,
    verify_password,
)
from src.security.authorization import Role


def _student(session, student_number: str) -> Student:
    return next(
        s for s in session.query(Student).all() if s.student_number == student_number
    )


def test_hash_password_never_stores_plaintext():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_authenticate_student_succeeds_with_correct_credentials(seeded_db):
    with get_session() as session:
        student = _student(session, "DEMO0001")
        set_student_password(session, student, "hunter2")

        identity = authenticate_student(session, "DEMO0001", "hunter2")

        assert identity.role == Role.STUDENT
        assert identity.student_id == student.id


def test_authenticate_student_rejects_wrong_password(seeded_db):
    with get_session() as session:
        student = _student(session, "DEMO0001")
        set_student_password(session, student, "hunter2")

        with pytest.raises(AuthenticationError):
            authenticate_student(session, "DEMO0001", "wrong-password")


def test_authenticate_student_rejects_unknown_student_number(seeded_db):
    with get_session() as session:
        with pytest.raises(AuthenticationError):
            authenticate_student(session, "NOT-A-REAL-STUDENT", "anything")


def test_authenticate_student_rejects_when_no_credential_set(seeded_db):
    """A student row can exist without a credential ever being seeded
    (e.g. a fresh import before seed_demo_credentials runs) - that must
    fail closed, not silently authenticate."""
    with get_session() as session:
        _student(session, "DEMO0001")  # exists, but no credential set

        with pytest.raises(AuthenticationError):
            authenticate_student(session, "DEMO0001", "anything")


def test_set_student_password_is_idempotent_and_replaces_existing(seeded_db):
    with get_session() as session:
        student = _student(session, "DEMO0001")
        set_student_password(session, student, "first-password")
        set_student_password(session, student, "second-password")

    with get_session() as session:
        identity = authenticate_student(session, "DEMO0001", "second-password")
        assert identity.student_id is not None

        with pytest.raises(AuthenticationError):
            authenticate_student(session, "DEMO0001", "first-password")


def test_authenticate_staff_succeeds_with_correct_credentials(clean_db):
    with get_session() as session:
        set_staff_password(session, "coordinator1", Role.STAFF, "s3cret")

        identity = authenticate_staff(session, "coordinator1", "s3cret")

        assert identity.role == Role.STAFF
        assert identity.student_id is None


def test_authenticate_staff_rejects_wrong_password(clean_db):
    with get_session() as session:
        set_staff_password(session, "admin1", Role.ADMIN, "s3cret")

        with pytest.raises(AuthenticationError):
            authenticate_staff(session, "admin1", "wrong")


def test_authenticate_staff_rejects_unknown_username(clean_db):
    with get_session() as session:
        with pytest.raises(AuthenticationError):
            authenticate_staff(session, "nobody", "anything")


def test_set_staff_password_rejects_student_role(clean_db):
    with get_session() as session:
        with pytest.raises(ValueError):
            set_staff_password(session, "someone", Role.STUDENT, "password")


def test_seed_demo_credentials_seeds_every_student_and_two_staff_accounts(seeded_db):
    """seeded_db already ran run_parse_stage(), which calls
    seed_demo_credentials - each demo student should be able to sign in
    with their own student number as the password, and the fixed staff/
    admin demo accounts should exist."""
    with get_session() as session:
        for student_number in ("DEMO0001", "DEMO0002", "DEMO0003"):
            identity = authenticate_student(session, student_number, student_number)
            assert identity.role == Role.STUDENT

        staff_identity = authenticate_staff(session, "staff", "staff123")
        assert staff_identity.role == Role.STAFF

        admin_identity = authenticate_staff(session, "admin", "admin123")
        assert admin_identity.role == Role.ADMIN


def test_seed_demo_credentials_is_idempotent(seeded_db):
    """Running the parse stage again (as the pipeline does on every run)
    must not reset an already-changed password back to the default."""
    from src.parse.cleaners import run_parse_stage

    with get_session() as session:
        student = _student(session, "DEMO0001")
        set_student_password(session, student, "a-changed-password")

    run_parse_stage()

    with get_session() as session:
        identity = authenticate_student(session, "DEMO0001", "a-changed-password")
        assert identity.student_id is not None

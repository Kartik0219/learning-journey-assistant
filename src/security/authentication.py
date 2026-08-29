"""Real password-based authentication (N1), replacing the demonstration
student/role picker in `src.deliver.app` with an actual credential check.

## What changed, and what didn't

Before this module, `src.deliver.app`'s login screen let a visitor *pick*
which demo student or role they were - no password, and that was
explicitly disclosed in that module's docstring as demonstration-only.
This module adds a real check: a submitted (student number, password) or
(username, password) pair is verified against a salted hash
(`UserCredential.password_hash`, src/db/models.py) using werkzeug's
PBKDF2-based `generate_password_hash`/`check_password_hash` - already a
transitive dependency via Flask, so this adds no new package. A wrong
password is now actually rejected, not just cosmetically gated.

What's still demonstration-scope, and disclosed as such: the *seeded*
passwords (`src.parse.cleaners.seed_demo_credentials`) are fixed and
documented, not secrets a real user chose. That is a project-scope
decision (there is no self-service sign-up flow, on purpose - this is an
academic assessment, not a production identity system), not a security
bug in the mechanism itself. `Everything downstream of authentication -
require_student_access, ensure_consent_active - is unchanged; this module
only replaces "how do you prove who you are".

N4: every sign-in attempt (success or failure) should be audit-logged by
the caller via `src.security.audit.log_event` with action "sign_in" or
"sign_in_failed" - that's done in `src.deliver.app`'s login route, not
here, since this module deliberately doesn't assume a web framework or
even that logging is wanted for every call site (e.g. it's reused by the
credential-seeding pipeline step, which shouldn't audit-log its own
setup).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from src.db.models import Student, UserCredential
from src.security.authorization import Role
from src.security.encryption import blind_index


class AuthenticationError(Exception):
    """Raised when a submitted identifier/password pair doesn't match a
    stored credential. Deliberately the same error and message shape
    whether the identifier is unknown or the password is wrong - telling
    an attacker which one failed is an unnecessary information leak."""


def hash_password(plaintext: str) -> str:
    """Salted PBKDF2 hash - never store or compare plaintext passwords."""
    return generate_password_hash(plaintext)


def verify_password(plaintext: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, plaintext)


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """What a successful `authenticate_*` call proves: a role, and (for a
    Student) which one. Callers turn this into a session the same way the
    old demo picker did - this module doesn't know about Flask sessions."""

    role: Role
    student_id: int | None = None


def set_student_password(session: Session, student: Student, plaintext: str) -> UserCredential:
    """Create or replace a Student's credential. Looked up by
    `student.id`, not `student_number` - callers already have the
    decrypted `Student` row by the time they need this (e.g. the seeding
    step, or a future "change password" feature), so there's no reason to
    re-derive a blind index here."""
    existing = session.query(UserCredential).filter_by(student_id=student.id).one_or_none()
    if existing:
        existing.password_hash = hash_password(plaintext)
        return existing
    credential = UserCredential(
        role=Role.STUDENT.value, student_id=student.id, password_hash=hash_password(plaintext)
    )
    session.add(credential)
    session.flush()
    return credential


def set_staff_password(
    session: Session, username: str, role: Role, plaintext: str
) -> UserCredential:
    """Create or replace a Staff/Admin credential, identified by
    `username` (there is no Student row to key off for these roles)."""
    if role == Role.STUDENT:
        raise ValueError("set_staff_password is for STAFF/ADMIN roles - use set_student_password.")
    existing = session.query(UserCredential).filter_by(username=username).one_or_none()
    if existing:
        existing.password_hash = hash_password(plaintext)
        existing.role = role.value
        return existing
    credential = UserCredential(
        role=role.value, username=username, password_hash=hash_password(plaintext)
    )
    session.add(credential)
    session.flush()
    return credential


def authenticate_student(
    session: Session, student_number: str, password: str
) -> AuthenticatedIdentity:
    """Verify a student-number/password pair. Looks the student up by
    the same blind index every other student_number lookup uses (N3 -
    the encrypted column itself can't be filtered on)."""
    student_hash = blind_index(student_number)
    student = session.query(Student).filter_by(student_number_hash=student_hash).one_or_none()
    if student is None:
        raise AuthenticationError("Incorrect student number or password.")

    credential = session.query(UserCredential).filter_by(student_id=student.id).one_or_none()
    if credential is None or not verify_password(password, credential.password_hash):
        raise AuthenticationError("Incorrect student number or password.")

    return AuthenticatedIdentity(role=Role.STUDENT, student_id=student.id)


def authenticate_staff(session: Session, username: str, password: str) -> AuthenticatedIdentity:
    """Verify a username/password pair for a Staff or Admin account."""
    credential = session.query(UserCredential).filter_by(username=username).one_or_none()
    if credential is None or credential.role not in (Role.STAFF.value, Role.ADMIN.value):
        raise AuthenticationError("Incorrect username or password.")
    if not verify_password(password, credential.password_hash):
        raise AuthenticationError("Incorrect username or password.")

    return AuthenticatedIdentity(role=Role(credential.role), student_id=None)

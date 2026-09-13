"""Server-side authorization checks (N1, N6).

N6: "The server must check authorisation on every request - a student
must never be able to open another student's data by changing an ID in
the URL." This module is the check that whatever Phase 4/6 dashboard
API gets built (IOG-40) must call before returning any student-scoped
data - it does not matter what a client sends, only what the server
verifies.

There is no login/session system in this repo yet, so `Actor` is a
plain, explicit value the caller constructs from whatever the future
auth layer decides "the current request" is - this module doesn't
assume a particular web framework.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class Role(str, enum.Enum):
    # The app is student-only: Staff and Admin roles were removed.
    STUDENT = "student"


@dataclass(frozen=True)
class Actor:
    """Whoever is making the request, as the server has authenticated them -
    never as claimed by request parameters."""

    role: Role
    student_id: int | None = None  # set when role is STUDENT


class AuthorizationError(PermissionError):
    """Raised when an actor requests data they are not entitled to see."""


def require_student_access(actor: Actor, target_student_id: int) -> None:
    """Enforce N6 for any endpoint that returns one student's data.

    Every actor is a student, and a student may only access their own
    `student_id`. Anything else is refused.
    """
    if actor.role != Role.STUDENT or actor.student_id != target_student_id:
        raise AuthorizationError(
            f"Actor (student_id={actor.student_id}) is not authorised to "
            f"access student_id={target_student_id}."
        )

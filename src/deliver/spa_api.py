"""JSON API for the React single-page app (`frontend/`).

The Jinja pages in src.deliver.app render server-side; the SPA needs the
same data as JSON. This blueprint is a thin transport layer only: every
endpoint goes through the same framework-free functions and the same
security checks the Jinja routes use - `require_student_access` (N6) and
`ensure_consent_active` (N2) - so the SPA cannot see anything the server-
rendered app would refuse to show.

Authentication is the existing Flask session cookie set by `/login`; the
SPA is served from the same origin (`/app/`), so no token handling or CORS
is involved. Unauthenticated calls get 401 and the SPA sends the browser
to `/login?next=/app/`.
"""

from __future__ import annotations

import re

from flask import Blueprint, abort, jsonify, request, session

from src.db.database import get_session
from src.db.models import Student, StudyRecommendation, Subject
from src.deliver.ai_insight_api import get_ai_insight
from src.deliver.dashboard_api import get_student_dashboard, get_student_resources, get_resource_library
from src.deliver.insight_api import get_student_insight
from src.estimate.mastery import record_engagement
from src.security.authorization import Actor, AuthorizationError, Role, require_student_access
from src.security.consent import ConsentError, ensure_consent_active

api = Blueprint("api", __name__, url_prefix="/api")

_SILO_CODE = re.compile(r"SILO\d+")


def _error(status: int, code: str, message: str):
    response = jsonify({"error": code, "message": message})
    response.status_code = status
    return response


@api.errorhandler(AuthorizationError)
def _forbidden(exc):
    return _error(403, "forbidden", "You do not have access to this record.")


@api.errorhandler(ConsentError)
def _no_consent(exc):
    return _error(
        403, "no_consent", "Consent is not active for this student, so no data is processed."
    )


def _actor() -> Actor:
    if "role" not in session:
        abort(_error(401, "not_signed_in", "Sign in first."))
    return Actor(role=Role(session["role"]), student_id=session.get("student_id"))


@api.get("/session")
def current_session():
    """Who is signed in, and which students they may view (N6: a student
    only ever gets themself in this list)."""
    actor = _actor()
    with get_session() as db:
        query = db.query(Student).order_by(Student.id)
        if actor.role == Role.STUDENT:
            query = query.filter(Student.id == actor.student_id)
        students = [{"id": s.id, "label": s.display_name} for s in query.all()]
    return jsonify({"role": actor.role.value, "student_id": actor.student_id, "students": students})


@api.get("/students/<int:student_id>/dashboard")
def dashboard(student_id: int):
    actor = _actor()
    with get_session() as db:
        return jsonify(get_student_dashboard(db, actor, student_id))


@api.get("/students/<int:student_id>/resources")
def resources(student_id: int):
    actor = _actor()
    with get_session() as db:
        return jsonify(get_student_resources(db, actor, student_id))


@api.get("/library")
def library():
    """Full study-material catalogue, all subjects/SILOs - any signed-in
    user may browse it (not personal student data, so no per-student
    access/consent gate, unlike /resources)."""
    _actor()
    with get_session() as db:
        return jsonify(get_resource_library(db))


@api.get("/students/<int:student_id>/insight")
def insight(student_id: int):
    """Plain-English reading of the student's results, computed from their
    own marks - deterministic and always available, unlike the LLM page."""
    actor = _actor()
    with get_session() as db:
        return jsonify(get_student_insight(db, actor, student_id))


@api.get("/students/<int:student_id>/ai-insight")
def ai_insight(student_id: int):
    """Opt-in LLM insight (IOG-52) - same access and consent gate, cached
    per student, and `enabled: false` when no provider is configured."""
    actor = _actor()
    with get_session() as db:
        return jsonify(get_ai_insight(db, actor, student_id))


@api.get("/students/<int:student_id>/results")
def results(student_id: int):
    """Assessment results grouped by subject, with the SILOs each result
    evidences. SILO codes come from the dataset's explicit SILO tags when
    present, otherwise from the *reviewed* skill gaps mapped from that
    result (F4 - unreviewed gaps are never exposed to a student)."""
    actor = _actor()
    with get_session() as db:
        require_student_access(actor, student_id)
        ensure_consent_active(db, student_id)
        student = db.get(Student, student_id)
        if student is None:
            abort(_error(404, "not_found", "No such student."))

        by_subject: dict[int, list[dict]] = {}
        for result in sorted(student.results, key=lambda r: r.id):
            if result.silo_tags_text:
                codes = _SILO_CODE.findall(result.silo_tags_text)
            else:
                codes = [
                    gap.learning_outcome.code
                    for gap in result.skill_gaps
                    if gap.reviewed and gap.learning_outcome is not None
                ]
            by_subject.setdefault(result.assessment.subject_id, []).append(
                {
                    "id": result.id,
                    "assessment": result.assessment.name,
                    "score": result.score,
                    "feedback": result.feedback_text,
                    "weight": result.weight,
                    "weighted_score": result.weighted_score,
                    "silo_codes": sorted(set(codes), key=lambda c: int(c[4:])),
                }
            )

        subjects = []
        for subject_id, rows in by_subject.items():
            subject = db.get(Subject, subject_id)
            scored = [r["score"] for r in rows if r["score"] is not None]
            subjects.append(
                {
                    "code": subject.code,
                    "name": subject.name,
                    "average_score": round(sum(scored) / len(scored), 1) if scored else None,
                    "assessments": rows,
                    "learning_outcomes": [
                        {"code": lo.code, "description": lo.description}
                        for lo in sorted(subject.learning_outcomes, key=lambda lo: int(lo.code[4:]))
                    ],
                }
            )
        return jsonify({"student": {"id": student.id, "display_name": student.display_name},
                        "subjects": subjects})


@api.post("/recommendations/<int:recommendation_id>/practice")
def practice(recommendation_id: int):
    """F11: mark a study recommendation as practised. JSON-only, so a plain
    cross-site HTML form cannot trigger it with the session cookie."""
    actor = _actor()
    if not request.is_json:
        abort(_error(415, "json_required", "Send application/json."))
    with get_session() as db:
        recommendation = db.get(StudyRecommendation, recommendation_id)
        if recommendation is None:
            abort(_error(404, "not_found", "No such recommendation."))
        require_student_access(actor, recommendation.student_id)
        ensure_consent_active(db, recommendation.student_id)
        record_engagement(db, recommendation.student, recommendation, completed=True)
    return jsonify({"ok": True})

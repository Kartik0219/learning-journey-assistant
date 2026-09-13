"""Phase 4/6 (IOG-40, IOG-31): the student-facing web dashboard (F10).

Run it with:

    python -m src.deliver.app

then open http://127.0.0.1:5000/ and sign in with a student number (the
password is the student number too, e.g. STU0001 / STU0001). The app is
student-only: there are no staff or admin accounts.

## Login is real, but demonstration-scoped

N1 asks for "login and role-based access for Student, Educator and
Administrator". This checks a real salted password hash
(`src.security.authentication`) against seeded `user_credentials` rows -
wrong passwords are rejected and every attempt is audit-logged, replacing
the earlier no-password demo picker (app-build phase, IOG-47). What's
still demonstration-scope, and disclosed as such in
docs/DATA_DICTIONARY.md ("Still open"): seeded accounts have fixed,
documented passwords, with no self-service sign-up or password-reset
flow - a deliberate scope boundary consistent with the tender's
"demonstration-level functionality" scope (Section 4.3), not a claim of
production-grade identity management. Everything downstream of login -
`require_student_access`, `ensure_consent_active` - is the same real,
tested IOG-42 security layer either way.

## App-build phase: Dashboard / My Plan / Quizzes / Resources tabs

The student view was originally one page (`/dashboard`) with every
outcome's mastery, recommendation, and quiz questions inline. It's now
split across four routes that share one `data` shape from
`get_student_dashboard` (Plan and Quizzes just filter it differently) -
`base.html` renders both a top nav (desktop) and a bottom tab bar
(mobile, <=600px) linking all four, so this is a navigation split, not
a new data model, apart from Resources' own `get_student_resources`.
"""

from __future__ import annotations

from pathlib import Path

from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from src.config import get_settings
from src.db.database import get_session
from src.db.models import Student
from src.deliver.ai_insight_api import get_ai_insight
from src.deliver.dashboard_api import (
    get_student_dashboard,
    get_student_resources,
    get_student_results,
)
from src.deliver.spa_api import api as spa_api
from src.estimate.mastery import record_engagement
from src.security.audit import log_event
from src.security.authentication import AuthenticationError, authenticate_student
from src.security.authorization import Actor, AuthorizationError, Role
from src.security.consent import ConsentError

# The React SPA's production build (`npm run build` in frontend/). Absent
# in a fresh clone or if the Node build step was skipped - /app then says so
# instead of erroring, and the server-rendered app is unaffected.
SPA_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def _safe_next(target: str | None) -> str | None:
    """Only same-site SPA paths are valid post-login destinations - never an
    absolute or protocol-relative URL (open-redirect guard)."""
    if target and target.startswith("/app") and not target.startswith("//"):
        return target
    return None


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = get_settings().app_secret_key
    app.register_blueprint(spa_api)

    @app.before_request
    def _drop_retired_roles():
        """Staff and Admin were removed; a browser still holding one of those
        old session cookies is simply signed out rather than erroring."""
        if session.get("role") not in (None, Role.STUDENT.value):
            session.clear()

    @app.route("/app/", defaults={"path": ""})
    @app.route("/app/<path:path>")
    def spa(path: str):
        """Serve the React SPA; unknown paths fall back to index.html so
        client-side routes (/app/results, /app/study-plan) survive a reload."""
        if not (SPA_DIST / "index.html").exists():
            message = "The React app has not been built: run `npm ci && npm run build` in frontend/"
            return (message, 404)
        if path and (SPA_DIST / path).is_file():
            return send_from_directory(SPA_DIST, path)
        return send_from_directory(SPA_DIST, "index.html")

    def _resolve_actor_and_target(db_session):
        """Shared by every tab route: the signed-in student, who only ever
        sees their own records (N6)."""
        actor = Actor(role=Role.STUDENT, student_id=session.get("student_id"))
        student = db_session.get(Student, actor.student_id)
        students = [{"id": student.id, "label": student.display_name}] if student else []
        return actor, students, actor.student_id

    @app.route("/")
    def index():
        if "role" in session:
            return redirect(url_for("dashboard"))
        return render_template("landing.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template("login.html", error=None)

        student_number = request.form.get("student_number", "").strip()
        password = request.form.get("password", "")
        if not student_number or not password:
            return render_template("login.html", error="Enter your student number and password.")

        with get_session() as db_session:
            try:
                identity = authenticate_student(db_session, student_number, password)
                # N4: sign-in is a named example event in AuditLogEntry's
                # own docstring - log by the identifier actually submitted,
                # since the encrypted student_number can't be queried back
                # out of identity.student_id cheaply here.
                log_event(db_session, actor=student_number, action="sign_in")
            except AuthenticationError as exc:
                # N4: failed attempts are audited too, without confirming
                # *which* field was wrong.
                log_event(db_session, actor=student_number, action="sign_in_failed")
                return render_template("login.html", error=str(exc))

        session["role"] = identity.role.value
        session["student_id"] = identity.student_id
        return redirect(_safe_next(request.args.get("next")) or url_for("dashboard"))

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    def dashboard():
        if "role" not in session:
            return redirect(url_for("login"))

        with get_session() as db_session:
            actor, students, target_student_id = _resolve_actor_and_target(db_session)
            try:
                data = get_student_dashboard(db_session, actor, target_student_id)
            except AuthorizationError:
                abort(403)
            except ConsentError:
                return render_template(
                    "no_consent.html", student_id=target_student_id, actor_role=actor.role.value
                )

            return render_template(
                "dashboard.html",
                data=data,
                actor_role=actor.role.value,
                students=students,
                current_student_id=target_student_id,
            )

    @app.route("/plan")
    def plan():
        """App-build phase (mobile nav scope-out): My Plan tab - the same
        per-outcome data as /dashboard, filtered in the template to just
        the outcomes that have a recommendation. No new query - F7/F8
        already put this on `data.outcomes[*].recommendation`."""
        if "role" not in session:
            return redirect(url_for("login"))

        with get_session() as db_session:
            actor, students, target_student_id = _resolve_actor_and_target(db_session)
            try:
                data = get_student_dashboard(db_session, actor, target_student_id)
            except AuthorizationError:
                abort(403)
            except ConsentError:
                return render_template(
                    "no_consent.html", student_id=target_student_id, actor_role=actor.role.value
                )

            return render_template(
                "plan.html",
                data=data,
                actor_role=actor.role.value,
                students=students,
                current_student_id=target_student_id,
            )

    @app.route("/quizzes")
    def quizzes():
        """App-build phase (mobile nav scope-out): Quizzes tab - same data
        source as /dashboard and /plan, filtered to outcomes that have
        quiz questions (F8)."""
        if "role" not in session:
            return redirect(url_for("login"))

        with get_session() as db_session:
            actor, students, target_student_id = _resolve_actor_and_target(db_session)
            try:
                data = get_student_dashboard(db_session, actor, target_student_id)
            except AuthorizationError:
                abort(403)
            except ConsentError:
                return render_template(
                    "no_consent.html", student_id=target_student_id, actor_role=actor.role.value
                )

            return render_template(
                "quizzes.html",
                data=data,
                actor_role=actor.role.value,
                students=students,
                current_student_id=target_student_id,
            )

    @app.route("/results")
    def results():
        """Every assessment result the student has, grouped by subject, with
        the workbook's own columns: type, score, feedback, SILOs, weight and
        weighted score."""
        if "role" not in session:
            return redirect(url_for("login"))

        with get_session() as db_session:
            actor, students, target_student_id = _resolve_actor_and_target(db_session)
            try:
                data = get_student_results(db_session, actor, target_student_id)
            except AuthorizationError:
                abort(403)
            except ConsentError:
                return render_template(
                    "no_consent.html", student_id=target_student_id, actor_role=actor.role.value
                )

            return render_template(
                "results.html",
                data=data,
                actor_role=actor.role.value,
                students=students,
                current_student_id=target_student_id,
            )

    @app.route("/resources")
    def resources():
        """App-build phase (mobile nav scope-out): Resources tab - browse
        the F9 grounding source materials for this student's subjects,
        rather than only ever seeing the one material a recommendation
        happened to cite."""
        if "role" not in session:
            return redirect(url_for("login"))

        with get_session() as db_session:
            actor, students, target_student_id = _resolve_actor_and_target(db_session)
            try:
                data = get_student_resources(db_session, actor, target_student_id)
            except AuthorizationError:
                abort(403)
            except ConsentError:
                return render_template(
                    "no_consent.html", student_id=target_student_id, actor_role=actor.role.value
                )

            return render_template(
                "resources.html",
                data=data,
                actor_role=actor.role.value,
                students=students,
                current_student_id=target_student_id,
            )

    @app.route("/ai-insight")
    def ai_insight():
        """IOG-52: opt-in AI (LLM) insight for the current student. Renders the
        natural-language SYSTEM_PROMPT analysis when a provider is configured,
        otherwise an "enable it" notice pointing back to the dashboard - the
        local TF-IDF view stays the source of truth either way."""
        if "role" not in session:
            return redirect(url_for("login"))

        with get_session() as db_session:
            actor, students, target_student_id = _resolve_actor_and_target(db_session)
            try:
                data = get_ai_insight(db_session, actor, target_student_id)
            except AuthorizationError:
                abort(403)
            except ConsentError:
                return render_template(
                    "no_consent.html", student_id=target_student_id, actor_role=actor.role.value
                )

            return render_template(
                "ai_insight.html",
                data=data,
                actor_role=actor.role.value,
                students=students,
                current_student_id=target_student_id,
            )

    @app.route("/practice/<int:recommendation_id>", methods=["POST"])
    def practice(recommendation_id: int):
        if "role" not in session:
            return redirect(url_for("login"))

        actor = Actor(role=Role.STUDENT, student_id=session.get("student_id"))
        student_id = request.form.get("student_id", type=int)

        with get_session() as db_session:
            try:
                from src.db.models import StudyRecommendation

                recommendation = db_session.get(StudyRecommendation, recommendation_id)
                if recommendation is None or recommendation.student_id != student_id:
                    abort(404)
                # F10/N6: re-check access even though the form told us who
                # the student is - never trust that field on its own.
                get_student_dashboard(db_session, actor, student_id)
                student = db_session.get(Student, student_id)
                record_engagement(db_session, student, recommendation, completed=True)
            except AuthorizationError:
                abort(403)
            except ConsentError:
                abort(403)

        # Recommendations now live on the My Plan tab, not /dashboard -
        # send the student back to where the button they just clicked was.
        return redirect(url_for("plan", student_id=student_id))

    return app

if __name__ == "__main__":
    create_app().run(debug=True)

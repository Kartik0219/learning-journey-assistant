"""Phase 4/6 (IOG-40, IOG-31): the student-facing web dashboard (F10).

Run it with:

    python -m src.deliver.app

then open http://127.0.0.1:5000/ - pick a demo student (or Staff/Admin)
on the login screen.

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

from flask import Flask, abort, redirect, render_template, request, session, url_for

from src.config import get_settings
from src.db.database import get_session
from src.db.models import Student
from src.deliver.ai_insight_api import get_ai_insight
from src.deliver.coordinator_api import get_coordinator_report
from src.deliver.dashboard_api import get_student_dashboard, get_student_resources
from src.estimate.mastery import record_engagement
from src.security.audit import log_event
from src.security.authentication import (
    AuthenticationError,
    authenticate_staff,
    authenticate_student,
)
from src.security.authorization import Actor, AuthorizationError, Role
from src.security.consent import ConsentError

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = get_settings().app_secret_key

    def _resolve_actor_and_target(db_session):
        """Shared by every tab route: who's asking, and which student are
        they looking at. A Student only ever sees themself (N6); Staff/
        Admin can switch students via `?student_id=`, and that choice is
        remembered in the session so it survives navigating between tabs
        without threading a query string through every nav link."""
        actor = Actor(role=Role(session["role"]), student_id=session.get("student_id"))
        students = [
            {"id": s.id, "label": s.display_name}
            for s in db_session.query(Student).order_by(Student.id).all()
        ]
        if actor.role == Role.STUDENT:
            return actor, students, actor.student_id

        requested = request.args.get("student_id", type=int)
        target_student_id = requested if requested is not None else session.get("viewed_student_id")
        if target_student_id is None:
            if not students:
                abort(404)
            target_student_id = students[0]["id"]
        session["viewed_student_id"] = target_student_id
        return actor, students, target_student_id

    @app.route("/")
    def index():
        if "role" in session:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template("login.html", error=None)

        role = request.form.get("role", "")
        password = request.form.get("password", "")

        with get_session() as db_session:
            try:
                if role == Role.STUDENT.value:
                    student_number = request.form.get("student_number", "")
                    if not student_number or not password:
                        return render_template(
                            "login.html", error="Enter your student number and password."
                        )
                    identity = authenticate_student(db_session, student_number, password)
                    # N4: sign-in is a named example event in AuditLogEntry's
                    # own docstring - log by the identifier actually
                    # submitted, since the encrypted student_number can't be
                    # queried back out of identity.student_id cheaply here.
                    log_event(db_session, actor=student_number, action="sign_in")
                elif role in (Role.STAFF.value, Role.ADMIN.value):
                    username = request.form.get("username", "")
                    if not username or not password:
                        return render_template(
                            "login.html", error="Enter your username and password."
                        )
                    identity = authenticate_staff(db_session, username, password)
                    log_event(db_session, actor=username, action="sign_in")
                else:
                    return render_template("login.html", error="Pick a role.")
            except AuthenticationError as exc:
                # N4: failed attempts are worth an audit trail too, but
                # never at the cost of confirming *which* field was wrong -
                # AuthenticationError's message already avoids that.
                failed_actor = (
                    request.form.get("student_number") or request.form.get("username") or "unknown"
                )
                log_event(db_session, actor=failed_actor, action="sign_in_failed")
                return render_template("login.html", error=str(exc))

        session["role"] = identity.role.value
        session["student_id"] = identity.student_id
        return redirect(url_for("dashboard"))

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
                is_staff=actor.role != Role.STUDENT,
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
                is_staff=actor.role != Role.STUDENT,
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
                is_staff=actor.role != Role.STUDENT,
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
                is_staff=actor.role != Role.STUDENT,
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
                is_staff=actor.role != Role.STUDENT,
                students=students,
                current_student_id=target_student_id,
            )

    @app.route("/coordinator")
    def coordinator():
        """App-build phase database feature (Staff/Admin only, N6): the
        cohort-level counterpart to /dashboard - see
        src.deliver.coordinator_api.get_coordinator_report."""
        if "role" not in session:
            return redirect(url_for("login"))

        actor = Actor(role=Role(session["role"]), student_id=session.get("student_id"))

        with get_session() as db_session:
            try:
                report = get_coordinator_report(db_session, actor)
            except AuthorizationError:
                abort(403)

            return render_template("coordinator.html", report=report, actor_role=actor.role.value)

    @app.route("/practice/<int:recommendation_id>", methods=["POST"])
    def practice(recommendation_id: int):
        if "role" not in session:
            return redirect(url_for("login"))

        actor = Actor(role=Role(session["role"]), student_id=session.get("student_id"))
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

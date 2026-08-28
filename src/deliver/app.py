"""Phase 4/6 (IOG-40, IOG-31): the student-facing web dashboard (F10).

Run it with:

    python -m src.deliver.app

then open http://127.0.0.1:5000/ - pick a demo student (or Staff/Admin)
on the login screen.

## Login is demonstration-level, and that's disclosed, not hidden

N1 asks for "login and role-based access for Student, Educator and
Administrator". There is no password system in this codebase - the
docs (docs/DATA_DICTIONARY.md "Still open") have said so from Phase 5
onwards, and this app doesn't quietly paper over that. The login screen
lets you pick which demo student/role you are, which is honest about
what it is: enough of a session (`flask.session`, a signed cookie) to
exercise real role-based access control end-to-end, not a claim that
credential-based authentication has been built. Everything downstream
of login - `require_student_access`, `ensure_consent_active` - is the
real, tested IOG-42 security layer; only "how do you prove who you
are" is stubbed, consistent with the tender's "demonstration-level
functionality" scope (Section 4.3).
"""

from __future__ import annotations

from flask import Flask, abort, redirect, render_template, request, session, url_for

from src.config import get_settings
from src.db.database import get_session
from src.db.models import Student
from src.deliver.dashboard_api import get_student_dashboard
from src.estimate.mastery import record_engagement
from src.security.authorization import Actor, AuthorizationError, Role
from src.security.consent import ConsentError


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = get_settings().app_secret_key

    @app.route("/")
    def index():
        if "role" in session:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        with get_session() as db_session:
            students = [
                {"id": s.id, "label": f"{s.display_name}"}
                for s in db_session.query(Student).order_by(Student.id).all()
            ]

            if request.method == "POST":
                role = request.form.get("role", "")
                if role == Role.STUDENT.value:
                    student_id = request.form.get("student_id", type=int)
                    if not student_id:
                        return render_template(
                            "login.html", students=students, error="Pick which student you are."
                        )
                    session["role"] = Role.STUDENT.value
                    session["student_id"] = student_id
                elif role in (Role.STAFF.value, Role.ADMIN.value):
                    session["role"] = role
                    session["student_id"] = None
                else:
                    return render_template(
                        "login.html", students=students, error="Pick a role."
                    )
                return redirect(url_for("dashboard"))

            return render_template("login.html", students=students, error=None)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    def dashboard():
        if "role" not in session:
            return redirect(url_for("login"))

        actor = Actor(role=Role(session["role"]), student_id=session.get("student_id"))

        # Staff/Admin can view any student's dashboard (that's what "no
        # cross-student access" means for a Student, not for those
        # roles - N6/N1); a Student always sees only their own.
        if actor.role == Role.STUDENT:
            target_student_id = actor.student_id
        else:
            target_student_id = request.args.get("student_id", type=int)

        with get_session() as db_session:
            students = [
                {"id": s.id, "label": s.display_name}
                for s in db_session.query(Student).order_by(Student.id).all()
            ]
            if target_student_id is None:
                if not students:
                    abort(404)
                target_student_id = students[0]["id"]

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

        return redirect(url_for("dashboard", student_id=student_id))

    return app


if __name__ == "__main__":
    create_app().run(debug=True)

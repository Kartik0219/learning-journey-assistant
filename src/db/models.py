"""Shared database schema.

Covers the domain entities for the whole five-stage pipeline: subjects,
learning outcomes (SILOs), rubrics, students, assessment results,
extracted skill gaps, mastery scores, topic materials, generated study
recommendations, and study engagement - plus the two compliance records
(consent, audit log) called for by N2 and N4.

Privacy note (IOG-42 / Phase 5): `Student.student_number` and
`Student.display_name` are encrypted at rest (N3) via
`src.security.encryption.EncryptedString` - see that module's docstring
for how the companion `student_number_hash` column keeps lookups
working on an encrypted column. Authorization (N6), audit logging (N4),
and consent gating (N2) are implemented as reusable primitives in
`src.security` and are wired into the dashboard (`src.deliver.app`,
IOG-40) as the gate every request goes through before touching a
student's rows. `feedback_text` below is still plain-text on purpose -
see its own comment.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from src.db.database import Base
from src.security.encryption import EncryptedString, blind_index


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # e.g. "CSE5IDP"
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, default=None)

    learning_outcomes: Mapped[list["LearningOutcome"]] = relationship(back_populates="subject")
    rubrics: Mapped[list["Rubric"]] = relationship(back_populates="subject")
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="subject")


class LearningOutcome(Base):
    """A subject's intended learning outcome (SILO)."""

    __tablename__ = "learning_outcomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    code: Mapped[str] = mapped_column(String(20))  # e.g. "SILO1"
    description: Mapped[str] = mapped_column(Text)

    subject: Mapped[Subject] = relationship(back_populates="learning_outcomes")


class Rubric(Base):
    __tablename__ = "rubrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    name: Mapped[str] = mapped_column(String(200))

    subject: Mapped[Subject] = relationship(back_populates="rubrics")
    criteria: Mapped[list["RubricCriterion"]] = relationship(back_populates="rubric")


class RubricCriterion(Base):
    """One row of a rubric, optionally linked to the SILO it assesses.

    That link (`learning_outcome_id`) is what F5 calls "linking gaps to
    learning outcomes" - it's nullable because the raw rubric data usually
    arrives without this mapping already made; Phase 1 data prep (IOG-34)
    is what starts filling it in, Phase 3 (IOG-37/38) does it properly with
    embeddings/similarity scoring.
    """

    __tablename__ = "rubric_criteria"

    id: Mapped[int] = mapped_column(primary_key=True)
    rubric_id: Mapped[int] = mapped_column(ForeignKey("rubrics.id"))
    learning_outcome_id: Mapped[int | None] = mapped_column(
        ForeignKey("learning_outcomes.id"), default=None
    )
    criterion_text: Mapped[str] = mapped_column(Text)

    rubric: Mapped[Rubric] = relationship(back_populates="criteria")
    learning_outcome: Mapped[LearningOutcome | None] = relationship()


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    # N3: encrypted at rest. This column can no longer be queried with
    # `filter_by(student_number=...)` - Fernet ciphertext is
    # non-deterministic, so use `student_number_hash` for lookups instead
    # (see src/security/encryption.py). Application code still just reads/
    # writes this as a plain string; the ORM handles encrypt/decrypt.
    # Column sized generously: Fernet ciphertext (IV + HMAC + padding,
    # base64-encoded) runs noticeably longer than the plaintext it wraps.
    student_number: Mapped[str] = mapped_column(EncryptedString(512))
    # Deterministic HMAC of the normalised student_number - this is what
    # every lookup/uniqueness check actually uses.
    student_number_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # N3: encrypted at rest. Never queried by value, only displayed, so it
    # doesn't need a companion hash column.
    display_name: Mapped[str] = mapped_column(EncryptedString(512))

    consent: Mapped["ConsentRecord | None"] = relationship(back_populates="student", uselist=False)
    results: Mapped[list["AssessmentResult"]] = relationship(back_populates="student")
    mastery_scores: Mapped[list["MasteryScore"]] = relationship(back_populates="student")

    @validates("student_number")
    def _keep_hash_in_sync(self, key: str, value: str) -> str:
        """Recompute student_number_hash whenever student_number is set, so
        it is never possible to create/update a Student with a stale or
        missing hash - callers just set student_number normally."""
        self.student_number_hash = blind_index(value)
        return value


class ConsentRecord(Base):
    """N2: process a student's data only after consent is recorded."""

    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), unique=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_date: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    withdrawn_date: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    student: Mapped[Student] = relationship(back_populates="consent")

    @property
    def is_active(self) -> bool:
        """Whether this student's data may currently be processed.

        F2/N2: "If consent is withdrawn, stop further processing for that
        student." Every pipeline stage that touches student-level data
        should check this before doing anything, not just at ingestion.
        """
        return self.consent_given and self.withdrawn_date is None


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    name: Mapped[str] = mapped_column(String(200))
    rubric_id: Mapped[int | None] = mapped_column(ForeignKey("rubrics.id"), default=None)

    subject: Mapped[Subject] = relationship(back_populates="assessments")
    results: Mapped[list["AssessmentResult"]] = relationship(back_populates="assessment")


class AssessmentResult(Base):
    """A single student's grade + written feedback for one assessment.

    This is the "grades" and "rubric comments" data IOG-34 is preparing.
    F12: this table is read-only from the official record's point of view -
    nothing in this codebase should ever write back to Moodle.
    """

    __tablename__ = "assessment_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    score: Mapped[float | None] = mapped_column(Float, default=None)
    # N5: this is unstructured, untrusted text from a human marker - never
    # feed it to a model as an instruction, only ever as data to analyse.
    feedback_text: Mapped[str | None] = mapped_column(Text, default=None)
    # Phase 6/IOG-33: the real provided dataset's explicit per-result SILO
    # tags ("SILO1: description; SILO2: description"), verbatim from its
    # "SILO's" column - still untrusted free text (N5) like feedback_text,
    # but structured enough that src.model.silo_mapping can parse it
    # directly instead of guessing relevance from feedback wording. None
    # for the synthetic sample dataset, which has no such column.
    silo_tags_text: Mapped[str | None] = mapped_column(Text, default=None)

    assessment: Mapped[Assessment] = relationship(back_populates="results")
    student: Mapped[Student] = relationship(back_populates="results")
    skill_gaps: Mapped[list["SkillGap"]] = relationship(back_populates="assessment_result")


class SkillGap(Base):
    """An extracted skill gap (F3/F4) - Phase 3's output, but the table
    lives here in Phase 1 so IOG-34's data prep has somewhere to land
    once extraction exists.

    F4: "Every extracted gap must point to a line in the rubric or
    feedback. Items with low confidence are held for review and are not
    shown to the student until checked" - hence `source_evidence_text`,
    `confidence`, and `reviewed` all being required, not optional extras.

    "until checked" means checked *by a person*. `review_status` and the
    staff review queue (src.deliver.review_api) are what make that true:
    before they existed, `reviewed` was set once at extraction time by a
    confidence comparison and never changed again, so nothing below the
    threshold could ever reach a student and no human ever checked
    anything. A threshold is a triage step, not a review.
    """

    __tablename__ = "skill_gaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_result_id: Mapped[int] = mapped_column(ForeignKey("assessment_results.id"))
    learning_outcome_id: Mapped[int | None] = mapped_column(
        ForeignKey("learning_outcomes.id"), default=None
    )
    source_evidence_text: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))  # e.g. "low" / "medium" / "high"
    confidence: Mapped[float] = mapped_column(Float)  # 0.0-1.0
    # Whether this gap may be shown to the student. Stays the single flag
    # every student-facing query filters on (src.deliver.dashboard_api).
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    # F4's review gate proper. `reviewed` alone cannot express it: False
    # there means both "nobody has looked at this yet" and "a human looked
    # and rejected it", so a rejected gap would sit in the review queue for
    # ever. These three columns record who decided what, and when:
    #   "pending"       - below the confidence threshold, awaiting a human
    #   "auto_approved" - at/above the threshold. F4 only requires that
    #                     *low* confidence items be held, so these pass
    #                     straight through, exactly as before this existed
    #   "approved"      - a human confirmed it (sets reviewed -> True)
    #   "rejected"      - a human rejected it (reviewed stays False, and it
    #                     leaves the queue instead of being offered again)
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    # Who decided, as the server authenticated them - a role label or staff
    # identifier, never a value supplied by the client (N6). Null while no
    # human has touched the row.
    reviewed_by: Mapped[str | None] = mapped_column(String(64), default=None)
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, default=None)
    # F7: "recommend a study method from a fixed table ... according to the
    # type of gap". Populated by src.model.silo_mapping from the verb of the
    # learning outcome the gap maps to (see that module's GAP_TYPE_METHODS
    # table) - null until a learning outcome has been assigned.
    gap_type: Mapped[str | None] = mapped_column(String(20), default=None)

    assessment_result: Mapped[AssessmentResult] = relationship(back_populates="skill_gaps")
    learning_outcome: Mapped[LearningOutcome | None] = relationship()


class MasteryScore(Base):
    """F6: weighted, explainable mastery estimate per student per SILO.

    Phase 4 (IOG-38/39/40) computes and updates these; the table exists
    now so Phase 1's schema is complete end-to-end and nothing has to be
    bolted on awkwardly later.
    """

    __tablename__ = "mastery_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    learning_outcome_id: Mapped[int] = mapped_column(ForeignKey("learning_outcomes.id"))
    score: Mapped[float] = mapped_column(Float)  # 0.0-1.0
    explanation_text: Mapped[str | None] = mapped_column(Text, default=None)
    last_updated: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    student: Mapped[Student] = relationship(back_populates="mastery_scores")
    learning_outcome: Mapped[LearningOutcome] = relationship()


class TopicMaterial(Base):
    """F9: subject topic materials, pre-split into short passages so the
    Estimate stage can retrieve the closest one and cite it as a source
    reference (F8's "check each generated item against the subject
    materials before it is shown" starts here - grounding by retrieval,
    not by asking a model to recall the material from memory).
    """

    __tablename__ = "topic_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    learning_outcome_id: Mapped[int | None] = mapped_column(
        ForeignKey("learning_outcomes.id"), default=None
    )
    title: Mapped[str] = mapped_column(String(200))
    passage_text: Mapped[str] = mapped_column(Text)

    subject: Mapped[Subject] = relationship()
    learning_outcome: Mapped[LearningOutcome | None] = relationship()


class StudyRecommendation(Base):
    """F7/F8: one generated study recommendation for a student on a
    learning outcome - the study method (from the fixed table, F7) plus
    grounded material text retrieved from a TopicMaterial passage (F8/F9).
    """

    __tablename__ = "study_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    learning_outcome_id: Mapped[int] = mapped_column(ForeignKey("learning_outcomes.id"))
    # retrieval_practice / spaced_practice / worked_example
    method: Mapped[str] = mapped_column(String(30))
    material_text: Mapped[str] = mapped_column(Text)
    source_topic_material_id: Mapped[int | None] = mapped_column(
        ForeignKey("topic_materials.id"), default=None
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    student: Mapped[Student] = relationship()
    learning_outcome: Mapped[LearningOutcome] = relationship()
    source_topic_material: Mapped[TopicMaterial | None] = relationship()


class StudyEngagement(Base):
    """F11: "store how the student engages with the recommended study
    materials and the plan, and use that information to update mastery
    estimates." One row per interaction; src.estimate.mastery reads these
    back in to nudge the relevant MasteryScore.
    """

    __tablename__ = "study_engagements"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    study_recommendation_id: Mapped[int] = mapped_column(ForeignKey("study_recommendations.id"))
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    engaged_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    student: Mapped[Student] = relationship()
    study_recommendation: Mapped[StudyRecommendation] = relationship()


class UserCredential(Base):
    """Real password sign-in credentials (N1), added alongside the app-
    build phase to replace the demonstration-only student/role picker in
    `src.deliver.app`.

    A separate table rather than a `password_hash` column on `Student`,
    because Staff/Admin accounts have no `Student` row to hang a column
    off - `username` is how those two are identified, `student_id` is how
    a Student is. Exactly one of the two is set, enforced in
    `src.security.authentication` rather than at the schema level (SQLite
    has no portable CHECK-constraint-with-XOR story worth the complexity
    here). Never stores a plaintext password, only a salted hash from
    `src.security.authentication.hash_password` (werkzeug's PBKDF2-based
    `generate_password_hash` - already a transitive dependency via Flask,
    so no new package). See that module's docstring for the honesty note
    this carries forward from the original login: the *mechanism* here is
    real, but the seeded demo passwords are fixed/known, same
    demonstration-scope disclosure `src.deliver.app` already made.
    """

    __tablename__ = "user_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(20))  # Role.value: student/staff/admin
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id"), unique=True, default=None
    )
    username: Mapped[str | None] = mapped_column(String(100), unique=True, default=None)
    password_hash: Mapped[str] = mapped_column(String(255))

    student: Mapped[Student | None] = relationship()


class QuizQuestion(Base):
    """A generated practice-quiz question (F8, app-build phase AI feature).

    Grounded the same way `StudyRecommendation.material_text` is (F8/F9):
    built from a template around a specific `SkillGap`'s own cited
    evidence plus the closest `TopicMaterial` passage found by
    `src.model.silo_mapping.best_similarity` (TF-IDF cosine similarity) -
    never freely generated, so there is nothing here a model could have
    hallucinated. `source_skill_gap_id` and `source_topic_material_id`
    make every question traceable back to the exact evidence and passage
    it was built from, the same evidentiary standard F4 already requires
    of skill gaps themselves.
    """

    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    learning_outcome_id: Mapped[int] = mapped_column(ForeignKey("learning_outcomes.id"))
    source_skill_gap_id: Mapped[int] = mapped_column(ForeignKey("skill_gaps.id"))
    source_topic_material_id: Mapped[int | None] = mapped_column(
        ForeignKey("topic_materials.id"), default=None
    )
    question_text: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(String(30))  # recall / apply / evaluate
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    student: Mapped[Student] = relationship()
    learning_outcome: Mapped[LearningOutcome] = relationship()
    source_skill_gap: Mapped[SkillGap] = relationship()
    source_topic_material: Mapped[TopicMaterial | None] = relationship()


class AuditLogEntry(Base):
    """N4: sign-in, consent changes, data import, study-plan/quiz creation.

    Append-only by convention - nothing in this codebase should ever
    UPDATE or DELETE a row here. Phase 5 (IOG-42) is where this actually
    gets wired into every relevant action; for now it's just the table.
    """

    __tablename__ = "audit_log_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(200))  # student_number, "system", etc.
    action: Mapped[str] = mapped_column(String(100))  # e.g. "consent_given", "data_import"
    target: Mapped[str | None] = mapped_column(String(200), default=None)
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

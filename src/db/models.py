"""Shared database schema.

Covers the domain entities needed to prepare data for Phase 1 (IOG-33,
IOG-34) and to give Phase 3/4 something concrete to build against:
subjects, learning outcomes (SILOs), rubrics, students, assessment
results, extracted skill gaps, and mastery scores - plus the two
compliance records (consent, audit log) called for by N2 and N4.

Privacy note (read before Phase 5 / IOG-42): this schema stores student
identifiers and free-text feedback in plain columns for now. Requirement
N3 ("encrypt stored student data") and N6 ("check authorisation on the
server for every request") are NOT implemented here - that's explicitly
IOG-42's scope. Don't treat this schema as production-ready for real
student data until that ticket lands. Fields most in scope are  called
out with a `# N3/N6:` comment below.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


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
    # N3/N6: student_number is the join key across every other table here -
    # it's the highest-value target for unauthorised access. Phase 5 should
    # decide whether this is encrypted at rest, pseudonymised, or protected
    # purely via access control at the query layer.
    student_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))

    consent: Mapped["ConsentRecord | None"] = relationship(back_populates="student", uselist=False)
    results: Mapped[list["AssessmentResult"]] = relationship(back_populates="student")
    mastery_scores: Mapped[list["MasteryScore"]] = relationship(back_populates="student")


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
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)

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

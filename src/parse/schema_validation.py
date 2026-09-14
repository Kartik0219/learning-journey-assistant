"""Expected shape of incoming records, enforced before anything touches
the database.

N5: "Treat imported rubric and feedback text as untrusted. Keep it
separate from system instructions, and reject model output that does
not match the required format." This module is the "reject anything
that doesn't match the required format" half of that for data coming
IN (Phase 3's src/model layer is responsible for validating what comes
OUT of the LLM, which is a separate concern).

Each Pydantic model below mirrors one of the sample CSVs in
data/sample/ - keep the two in sync if you add/rename a column.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class SubjectRecord(BaseModel):
    subject_code: str = Field(min_length=1, max_length=20)
    subject_name: str = Field(min_length=1, max_length=200)
    description: str | None = None

    @field_validator("subject_code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()


class LearningOutcomeRecord(BaseModel):
    subject_code: str
    silo_code: str
    description: str = Field(min_length=1)

    @field_validator("subject_code", "silo_code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()


class RubricCriterionRecord(BaseModel):
    subject_code: str
    rubric_name: str
    criterion_text: str = Field(min_length=1)
    silo_code: str | None = None

    @field_validator("subject_code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("silo_code")
    @classmethod
    def uppercase_optional_code(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else None


class StudentRecord(BaseModel):
    # F2: "match student and subject identifiers" - student_number is the
    # match key, so it's validated strictly rather than left as free text.
    student_number: str = Field(min_length=1, max_length=50)
    display_name: str = Field(min_length=1, max_length=200)

    @field_validator("student_number")
    @classmethod
    def normalise_student_number(cls, v: str) -> str:
        return v.strip().upper()


class AssessmentResultRecord(BaseModel):
    subject_code: str
    assessment_name: str
    student_number: str
    score: float | None = Field(default=None, ge=0, le=100)
    feedback_text: str | None = None
    # Phase 6/IOG-33: the real provided dataset's "SILO's" column -
    # explicit "SILO1: description; SILO2: description" tags stating
    # which learning outcomes this result actually covers. None for the
    # synthetic sample dataset, which has no such column - Phase 3's
    # extraction (src.model.silo_mapping) falls back to its older
    # feedback-text heuristic whenever this is absent.
    silo_tags_text: str | None = None
    # The real workbook's "Weight" (share of the subject total, 0-1) and
    # "Weighted Score" (score x weight) columns, shown as-is on the
    # student's Results page. Absent from the sample CSVs.
    weight: float | None = Field(default=None, ge=0, le=1)
    weighted_score: float | None = Field(default=None, ge=0, le=100)

    @field_validator("subject_code", "student_number")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()


class TopicMaterialRecord(BaseModel):
    """F1/F9: subject topic materials, split into short passages so Phase 4
    can retrieve and cite the closest one when generating study material."""

    subject_code: str
    silo_code: str | None = None
    title: str = Field(min_length=1, max_length=200)
    passage_text: str = Field(min_length=1)
    source_url: str | None = None
    provenance: str = "subject"

    @field_validator("subject_code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("source_url")
    @classmethod
    def https_only(cls, v: str | None) -> str | None:
        # N5: a link handed to students must be a real https URL - never
        # javascript:, file:, plain http, or a bare domain the browser guesses at.
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not v.startswith("https://"):
            raise ValueError("source_url must start with https://")
        return v

    @field_validator("provenance")
    @classmethod
    def known_provenance(cls, v: str) -> str:
        v = (v or "subject").strip().lower()
        if v not in {"subject", "curated"}:
            raise ValueError("provenance must be 'subject' or 'curated'")
        return v

    @field_validator("silo_code")
    @classmethod
    def uppercase_optional_code(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else None

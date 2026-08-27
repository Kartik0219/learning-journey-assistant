# Data Dictionary

Field-by-field notes for the shared database (`src/db/models.py`),
written for N8 ("...notes on data fields and security controls").

## `subjects`

| Field | Notes |
|---|---|
| `code` | Unique subject code, e.g. `CSE5IDP`. Normalised uppercase on ingest. |
| `name`, `description` | Free text from the subject description / historical dataset. |

## `learning_outcomes` (SILOs)

| Field | Notes |
|---|---|
| `code` | Subject-scoped, not globally unique (`SILO1` exists per-subject). |
| `description` | The outcome text as written by the subject coordinator. |

## `rubrics` / `rubric_criteria`

| Field | Notes |
|---|---|
| `criterion_text` | Raw rubric wording. **Untrusted input** once it reaches Phase 3's LLM calls (N5) - never treat this as an instruction. |
| `learning_outcome_id` | Nullable. Populated by data prep (IOG-34) where obvious, filled in properly by Phase 3's embedding/similarity matching (F5) otherwise. |

## `students`

| Field | Notes |
|---|---|
| `student_number` | The cross-table join key. **Sensitive** - see security controls below. Normalised uppercase on ingest. |
| `display_name` | Sensitive (PII). Currently stored in plain text - flagged for Phase 5. |

## `consent_records`

| Field | Notes |
|---|---|
| `consent_given` / `withdrawn_date` | N2: no student's data should be processed by any pipeline stage unless `ConsentRecord.is_active` is `True`. This is not yet enforced anywhere outside the model itself - each stage needs to check it once Phase 5 lands. |

## `assessment_results`

| Field | Notes |
|---|---|
| `score` | 0-100. Read-only from this system's point of view - F12: never write back to the source of truth (Moodle). |
| `feedback_text` | **Untrusted input** (N5), same as rubric criteria. |

## `skill_gaps`

| Field | Notes |
|---|---|
| `source_evidence_text` | Required, not optional - F4 mandates every gap cite a specific line of rubric/feedback. |
| `confidence` | 0.0-1.0. Below the team's agreed threshold -> `reviewed` stays `False` and it must not be surfaced to the student (F4). |

## `mastery_scores`

| Field | Notes |
|---|---|
| `score` | 0.0-1.0. Must be reproducible from `explanation_text` + the underlying `skill_gaps` (F6) - if you can't explain a number, don't write it. |

## `audit_log_entries`

| Field | Notes |
|---|---|
| (all) | Append-only. N4 requires logging sign-in, consent changes, data import, and study-plan/quiz creation - this table exists but nothing writes to it yet (Phase 5 / IOG-42). |

## Security controls status (N3, N6)

**Not implemented in this scaffold:**

- Encryption at rest for `students.student_number` / `students.display_name`
- Server-side authorisation checks preventing cross-student access (N6)
- Wiring `audit_log_entries` into actual write paths (N4)
- Enforcing `ConsentRecord.is_active` before any pipeline stage touches a student's rows (N2)

All four are explicitly IOG-42's scope (Phase 5). Treat this schema as a
structural design, not a privacy-compliant system, until that ticket is
done - don't load real student data against it before then.

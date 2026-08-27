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
| `student_number` | The cross-table join key. **Encrypted at rest** (N3, `EncryptedString`) — the ORM decrypts transparently on read. Never queryable by value directly; use `student_number_hash`. Normalised uppercase before encryption. |
| `student_number_hash` | Deterministic HMAC-SHA256 of the normalised `student_number` — unique/indexed, and what every lookup actually filters on, since encrypted ciphertext isn't stable across writes. Kept in sync automatically by a model-level validator; never set it by hand. |
| `display_name` | **Encrypted at rest** (N3, `EncryptedString`). Only ever read for display, never filtered on, so it has no companion hash column. |

## `consent_records`

| Field | Notes |
|---|---|
| `consent_given` / `withdrawn_date` | N2: no student's data should be processed by any pipeline stage unless `ConsentRecord.is_active` is `True`. Enforced via `src.security.consent.ensure_consent_active()` — every stage beyond basic identity provisioning must call it before touching that student's rows. Not yet called by Phases 3/4 because those stages don't exist yet; it *is* called (and tested) from the Phase 4 dashboard stub as a contract for whoever builds it. |

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
| `actor` | A `student_number` or `"system"`. Stored in **plain text on purpose** — an audit trail staff can actually read during a review is the point of N4; encrypting the actor field would defeat that. This is a deliberate scope boundary, not an oversight. |
| (all) | Append-only — write with `src.security.audit.log_event()`, never construct a row by hand or `UPDATE`/`DELETE` one. Currently written on every `run_parse_stage()` call (`data_import`) and every `record_consent()` call (`consent_given` / `consent_withdrawn`). Sign-in and quiz/plan-creation events will be added once Phases 4/6 build the features that produce them. |

## Security controls status (N3, N4, N6 — IOG-42)

**Implemented, in `src/security/`:**

- Encryption at rest for `students.student_number` / `students.display_name` (`encryption.py`, `EncryptedString` + `blind_index()` for lookups)
- Server-side authorization primitive for "can this actor see this student's data" (`authorization.py`, `require_student_access()`) — wired into the Phase 4 dashboard stub as a contract
- Audit logging (`audit.py`, `log_event()`) — wired into data import and consent changes
- Consent gating (`consent.py`, `ensure_consent_active()` / `record_consent()`) — wired into the Phase 4 dashboard stub as a contract

**Still open:**

- No login/session system exists yet (that's Phase 4/6, IOG-40), so `Actor` is currently constructed by hand in tests rather than derived from a real authenticated request — the primitive is ready, the caller isn't built.
- Sign-in and quiz/plan-creation audit events, since those features don't exist yet.
- Key rotation / secrets management beyond `.env` — fine for this academic scope, not production-grade.

See `tests/test_security.py` for the enforcement behaviour (encryption round-trips through the ORM but not the raw DB row, consent blocks with no record and after withdrawal, cross-student access is rejected, and the dashboard stub proves it can't be reached without passing both checks).

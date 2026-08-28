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
| `consent_given` / `withdrawn_date` | N2: no student's data should be processed by any pipeline stage unless `ConsentRecord.is_active` is `True`. Enforced via `src.security.consent.ensure_consent_active()`. `src.pipeline.run_estimate_stage()` calls this per student *before* running Phase 4 for them — a student with no active consent is skipped entirely, not just hidden later. The dashboard (`src.deliver.dashboard_api.get_student_dashboard()`) calls it again before assembling that student's view. The bundled sample dataset's consent is seeded via the real `record_consent()` API in `src.parse.cleaners.seed_demo_consent()` — same code path and audit trail a genuine consent flow would use, not a bypass. |

## `assessment_results`

| Field | Notes |
|---|---|
| `score` | 0-100. Read-only from this system's point of view - F12: never write back to the source of truth (Moodle). |
| `feedback_text` | **Untrusted input** (N5), same as rubric criteria. |

## `skill_gaps`

| Field | Notes |
|---|---|
| `source_evidence_text` | Required, not optional - F4 mandates every gap cite a specific line of rubric/feedback. Populated verbatim from a clause of `assessment_results.feedback_text` by `src.model.silo_mapping.extract_skill_gaps()` — nothing is written here that wasn't literally present in the input (N5). |
| `confidence` | 0.0-1.0. TF-IDF (character n-gram) cosine similarity between the evidence clause and the closest rubric criterion. Below `CONFIDENCE_REVIEW_THRESHOLD` (0.15) -> `reviewed` stays `False` and it must not be surfaced to the student (F4) — enforced in `src.deliver.dashboard_api.get_student_dashboard()`, which only ever includes `reviewed=True` gaps in a student's outcomes. |
| `learning_outcome_id` | Set by `src.model.silo_mapping.map_gap_to_learning_outcome()` (F5) — TF-IDF similarity against the subject's learning-outcome descriptions, left `None` rather than forced onto a weak match below `LO_MAPPING_THRESHOLD` (0.08). |
| `gap_type` | `conceptual` / `application` / `evaluation`, derived deterministically from the matched learning outcome's verb (`gap_type_for()`). Feeds `src.estimate.mastery`'s fixed study-method table (F7); `None` until a learning outcome has been assigned. |

## `mastery_scores`

| Field | Notes |
|---|---|
| `score` | 0.0-1.0. `src.estimate.mastery.calculate_mastery_score()` (F6): `clip(mean_assessment_score/100 - Σ(severity_weight × confidence) over reviewed gaps + engagement_bonus, 0, 1)`. Must be reproducible from `explanation_text` + the underlying `skill_gaps` - if you can't explain a number, don't write it. |
| `explanation_text` | Built from a template naming the exact baseline percentage, every contributing gap's quote/severity/confidence, and any engagement bonus applied — never freely generated. |

## `topic_materials`

| Field | Notes |
|---|---|
| `passage_text` | Short subject-material passage (F9), pre-split so Estimate can retrieve the closest one by similarity and cite it verbatim rather than asking a model to recall it from memory. |
| `learning_outcome_id` | Nullable. When set, `generate_study_material()` prefers this SILO's tagged passages before falling back to the whole subject. |

## `study_recommendations`

| Field | Notes |
|---|---|
| `method` | `worked_example` / `retrieval_practice` / `spaced_practice` — looked up from `STUDY_METHOD_TABLE` by gap type (F7), never chosen by a model. |
| `material_text` | Templated around `source_topic_material`'s own words, with a citation — grounded by retrieval (F8/F9), not generated freely, so nothing here can be hallucinated. |
| `source_topic_material_id` | Nullable — `None` (with `material_text` saying so plainly) when the subject has no topic material yet, rather than fabricating content. |

## `study_engagements`

| Field | Notes |
|---|---|
| `completed` | F11: recording a completion via `src.estimate.mastery.record_engagement()` immediately recalculates the affected `mastery_scores` row with a small, capped bonus (`ENGAGEMENT_BONUS_PER_COMPLETION`, capped at `ENGAGEMENT_BONUS_CAP`) rather than waiting for the next pipeline run. |

## `audit_log_entries`

| Field | Notes |
|---|---|
| `actor` | A `student_number` or `"system"`. Stored in **plain text on purpose** — an audit trail staff can actually read during a review is the point of N4; encrypting the actor field would defeat that. This is a deliberate scope boundary, not an oversight. |
| (all) | Append-only — write with `src.security.audit.log_event()`, never construct a row by hand or `UPDATE`/`DELETE` one. Currently written on every `run_parse_stage()` call (`data_import`) and every `record_consent()` call (`consent_given` / `consent_withdrawn`). Sign-in and quiz/plan-creation events will be added once Phases 4/6 build the features that produce them. |

## Security controls status (N3, N4, N6 — IOG-42)

**Implemented, in `src/security/`:**

- Encryption at rest for `students.student_number` / `students.display_name` (`encryption.py`, `EncryptedString` + `blind_index()` for lookups)
- Server-side authorization primitive for "can this actor see this student's data" (`authorization.py`, `require_student_access()`) — wired into the real Phase 4 dashboard (`src.deliver.dashboard_api.get_student_dashboard()`, IOG-40), and re-validated a second time on the `/practice` completion endpoint since that one takes `student_id` from form data
- Audit logging (`audit.py`, `log_event()`) — wired into data import and consent changes
- Consent gating (`consent.py`, `ensure_consent_active()` / `record_consent()`) — wired into the Estimate stage (per-student, before scoring) and into the dashboard

**Still open:**

- `src.deliver.app` has a lightweight, session-based "login" (pick a demo student number, no password) so the dashboard is reachable end-to-end for a demo — it is explicitly documented in that module as not a real authentication system, and is a separate concern from the RBAC/consent checks above, which are real and exercised through it. A production login system is out of this academic project's scope.
- Key rotation / secrets management beyond `.env` — fine for this academic scope, not production-grade.

See `tests/test_security.py` for the authorization/consent/encryption/audit enforcement behaviour (including that a cross-student dashboard request fails before any of the other student's rows are read), and `tests/test_estimate_mastery.py` / `tests/test_deliver_dashboard.py` for Phase 3/4's own behaviour built on top of those gates.

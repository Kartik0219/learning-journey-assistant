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
| `learning_outcome_id` | Nullable. Only ever set by data prep (IOG-34) when the source data supplies one explicit, single SILO code for that criterion - there is no similarity-matching fallback for this field (unlike `skill_gaps.learning_outcome_id`, see F5 below). Not read anywhere downstream (mastery scoring, recommendations, and quizzes all key off `skill_gaps.learning_outcome_id` instead), so this field's completeness has no effect on the dashboard - it exists purely as browsable rubric metadata. |

**Real dataset (IOG-33) note:** every rubric criterion for the real dataset is one Assessment Map row, which typically covers *several* SILOs at once (see that row's own `SILO Theme Summary`) - but `learning_outcome_id` is a single-valued foreign key. `src.connect.excel_loader.load_rubrics()` deliberately leaves `silo_code` blank for these rows rather than picking one SILO out of several and forcing a false single-outcome link (N5's grounding principle applied to metadata, not just generated text). All 11 real-dataset rubric criteria are expected to show `learning_outcome_id: None` - this is by design, not a bug.

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
| `silo_tags_text` | Phase 6/IOG-33. Verbatim copy of the real provided dataset's `SILO's` column ("SILO1: description; SILO2: description"), carried through by `src.connect.excel_loader.load_assessment_results()`. `None` for the synthetic sample dataset, which has no such column. This is what lets `src.model.silo_mapping.extract_skill_gaps()` use explicit institutional tags instead of guessing from feedback wording - see that section below. Still untrusted free text (N5) like `feedback_text`, just structured enough to parse deterministically (`src.connect.excel_loader.parse_silo_tags()`). |

## `skill_gaps`

Two extraction paths, chosen per result by whether `silo_tags_text` is
set (Phase 6/IOG-33 - see `src/model/silo_mapping.py`'s module
docstring for the full rationale):

| Field | Real-dataset path (`silo_tags_text` set) | Sample-dataset path (unset, original heuristic) |
|---|---|---|
| `source_evidence_text` | The verbatim `"SILOn: description"` tag. | A verbatim clause of `feedback_text`, split on punctuation/connectives. Required either way - not optional - F4 mandates every gap cite a specific line of rubric/feedback (N5: nothing paraphrased). |
| `severity` | Score band: `<50` high, `50-69` medium, `70-79` low. No gap at all is recorded for a tagged SILO on a result scoring `>= MASTERY_THRESHOLD` (80). | Keyword-marker match (`HIGH_SEVERITY_MARKERS` / `LOW_SEVERITY_MARKERS`), else `medium`. |
| `confidence` | Fixed `1.0` (`SILO_TAG_CONFIDENCE`) - an explicit institutional tag is a stated fact about the result, not an inference. | TF-IDF (character n-gram) cosine similarity between the evidence clause and the closest rubric criterion. Below `CONFIDENCE_REVIEW_THRESHOLD` (0.15) -> `reviewed` stays `False`. |
| `reviewed` | Always `True`. | `confidence >= CONFIDENCE_REVIEW_THRESHOLD`. Either way, only `reviewed=True` gaps may be surfaced to the student (F4) — enforced in `src.deliver.dashboard_api.get_student_dashboard()`. |
| `learning_outcome_id` | Set by `map_gap_to_learning_outcome()`'s exact-SILO-code match (the tag names its own code) — see next row. | Set by the same function's TF-IDF-similarity fallback, unchanged from the original design. |

`learning_outcome_id` (both paths): set by
`src.model.silo_mapping.map_gap_to_learning_outcome()` (F5). Tries an
exact SILO-code match first (only ever succeeds for the real-dataset
path, whose evidence text names its own code); falls back to TF-IDF
similarity against the subject's learning-outcome descriptions
otherwise, left `None` rather than forced onto a weak match below
`LO_MAPPING_THRESHOLD` (0.08).

| Field | Notes |
|---|---|
| `gap_type` | `conceptual` / `application` / `evaluation`, derived deterministically from the matched learning outcome's verb (`gap_type_for()`). Feeds `src.estimate.mastery`'s fixed study-method table (F7); `None` until a learning outcome has been assigned. Unaffected by which extraction path produced the gap. |

## `mastery_scores`

| Field | Notes |
|---|---|
| `score` | 0.0-1.0. `src.estimate.mastery.calculate_mastery_score()` (F6): `clip(mean_assessment_score/100 - Σ(severity_weight × confidence) over reviewed gaps + engagement_bonus, 0, 1)`. Must be reproducible from `explanation_text` + the underlying `skill_gaps` - if you can't explain a number, don't write it. Unchanged by the Phase 6 real-dataset work - it reads `severity`/`confidence`/`learning_outcome_id` off `skill_gaps` the same way regardless of which extraction path wrote them. |
| `explanation_text` | Built from a template naming the exact baseline percentage, every contributing gap's quote/severity/confidence, and any engagement bonus applied — never freely generated. |

## `topic_materials`

| Field | Notes |
|---|---|
| `passage_text` | Short subject-material passage (F9), pre-split so Estimate can retrieve the closest one by similarity and cite it verbatim rather than asking a model to recall it from memory. |
| `learning_outcome_id` | Nullable. When set, `generate_study_material()` prefers this SILO's tagged passages before falling back to the whole subject. |

**Real dataset (IOG-33) note:** `src.connect.excel_loader.load_topic_materials()`
returns an empty, correctly-shaped frame — the real workbook has no
topic-material passages at all. `src.estimate.mastery` already has an
honest fallback ("No topic material is available yet... flagged for
the subject coordinator") for exactly this case, so real-dataset
students get truthful recommendations, not hallucinated study material.

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

## `user_credentials` (app-build phase — Farshad, backend)

| Field | Notes |
|---|---|
| `role` | `student` / `staff` / `admin` (`Role.value`). |
| `student_id` | Set for a `student` credential, unique, FK to `students`. `None` for staff/admin. |
| `username` | Set for a `staff`/`admin` credential, unique. `None` for a student credential. |
| `password_hash` | Salted PBKDF2 hash (werkzeug `generate_password_hash`) — never a plaintext password. Checked by `src.security.authentication.authenticate_student` / `authenticate_staff`, called from `src.deliver.app`'s `/login` route. Seeded idempotently by `src.parse.cleaners.seed_demo_credentials` — see docs/ENVIRONMENT_SETUP.md's "Demo accounts" table for the fixed demo values. |

## `quiz_questions` (app-build phase — Prabhashi, AI feature)

| Field | Notes |
|---|---|
| `question_text` | Templated, never freely generated (N5) — built from a specific `SkillGap.source_evidence_text` (itself a verbatim quote) plus the closest `TopicMaterial` passage by TF-IDF cosine similarity (`src.model.silo_mapping.best_similarity`), the same grounding-by-retrieval pattern `study_recommendations.material_text` already uses. See `src/estimate/quiz.py`. |
| `question_type` | `recall` / `apply` / `evaluate` — derived deterministically from the mapped learning outcome's gap type (`src.model.silo_mapping.gap_type_for`), the same classification F7's study-method table already uses. Not a model's judgment call. |
| `source_skill_gap_id` | The specific reviewed `SkillGap` this question was built from — F4's evidentiary standard applied to quiz questions too. |
| `source_topic_material_id` | Nullable — `None` when the subject has no topic material yet, same honest fallback as `study_recommendations.source_topic_material_id`. |

## `audit_log_entries`

| Field | Notes |
|---|---|
| `actor` | A `student_number` or `"system"`. Stored in **plain text on purpose** — an audit trail staff can actually read during a review is the point of N4; encrypting the actor field would defeat that. This is a deliberate scope boundary, not an oversight. |
| (all) | Append-only — write with `src.security.audit.log_event()`, never construct a row by hand or `UPDATE`/`DELETE` one. Written on every `run_parse_stage()` call (`data_import`), every `record_consent()` call (`consent_given` / `consent_withdrawn`), and now every login attempt too (`sign_in` / `sign_in_failed`, from `src.deliver.app`'s `/login` route, app-build phase). Quiz-creation isn't separately audit-logged — `quiz_questions` rows are themselves the record, written by the same `run_estimate_stage` pipeline step as `mastery_scores`/`study_recommendations`, none of which get a per-row audit entry either. |

## Security controls status (N3, N4, N6 — IOG-42)

**Implemented, in `src/security/`:**

- Encryption at rest for `students.student_number` / `students.display_name` (`encryption.py`, `EncryptedString` + `blind_index()` for lookups)
- Server-side authorization primitive for "can this actor see this student's data" (`authorization.py`, `require_student_access()`) — wired into the real Phase 4 dashboard (`src.deliver.dashboard_api.get_student_dashboard()`, IOG-40), and re-validated a second time on the `/practice` completion endpoint since that one takes `student_id` from form data
- Audit logging (`audit.py`, `log_event()`) — wired into data import and consent changes
- Consent gating (`consent.py`, `ensure_consent_active()` / `record_consent()`) — wired into the Estimate stage (per-student, before scoring) and into the dashboard

**Still open:**

- `src.deliver.app`'s login now does a real password check (`src.security.authentication`, app-build phase) — salted hashes, wrong passwords rejected, every attempt audit-logged — rather than the earlier no-password picker. What's still demonstration-scope: seeded accounts have fixed, documented passwords (no self-service sign-up, no password reset flow) — a deliberate scope boundary for an academic project, not a claim of production-grade identity management. RBAC/consent checks downstream of login are unchanged and remain real.
- Key rotation / secrets management beyond `.env` — fine for this academic scope, not production-grade.
- **Dataset provenance (IOG-33):** whether `CSE_results_150_students_3_Subjects.xlsx` is a tutor-issued file or team-generated data is not yet confirmed by Ge Su (the ticket's assignee) - the tender brief states "no student data given, team generates it," which this file may or may not satisfy. Not blocking on this: the loader and extraction logic work correctly against the file's actual shape regardless of its origin, but the origin needs to be stated accurately in the final report, so this stays open until confirmed.

See `tests/test_security.py` for the authorization/consent/encryption/audit enforcement behaviour (including that a cross-student dashboard request fails before any of the other student's rows are read), and `tests/test_estimate_mastery.py` / `tests/test_deliver_dashboard.py` for Phase 3/4's own behaviour built on top of those gates.

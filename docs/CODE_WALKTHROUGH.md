# Code walkthrough — how the important parts work, and why they exist

This is the "read this first" guide for anyone opening the codebase: a
marker, a new team member, or the coordinator who inherits the app. It
explains the handful of modules that carry the product's promises, what
each one does, and the reason it is built the way it is. For installation
and operations see `SYSTEM_MAINTENANCE.md`; for the student's view see
`USER_GUIDE.md`; for every table and column see `DATA_DICTIONARY.md`.

The app makes four promises, and almost every design decision below traces
back to one of them:

| Promise | Requirement | Where it is enforced |
|---|---|---|
| Nothing is ever written back to Moodle or changes an official grade | F12 | `src/connect/` only reads; no write path exists |
| Every number a student sees can be traced to their own marked work | F4, F6 | `src/model/silo_mapping.py`, `src/estimate/mastery.py` |
| A student sees only their own record, and nothing is computed without consent | N2, N6 | `src/security/authorization.py`, `src/security/consent.py` |
| Study material is real, never invented by a model | F8, F9 | `src/estimate/mastery.py`, `data/dataset/curated_resources.csv` |

---

## 1. The shape of the system

```
data (xlsx / csv)  ──►  CONNECT ──► PARSE ──► MODEL ──► ESTIMATE ──► SQLite
                        (read)     (validate,  (skill    (mastery,
                                    upsert)    gaps →    plan, quiz)
                                               SILOs)
                                                                       │
                                        DELIVER (Flask) ◄──────────────┘
                                        ├── /login, /logout         (Jinja)
                                        ├── /api/students/<id>/…    (JSON, session cookie)
                                        └── /app/…  React student app (frontend/dist)
```

`python -m src.pipeline` runs the four batch stages in order
(`src/pipeline.py`). The web layer never computes anything heavy at request
time: it reads what the pipeline wrote. That split is deliberate — a page
load can never trigger a model call or a recomputation, so the app is fast,
cheap and predictable, and every number on screen is the same number that
was stored.

The stages are plain Python functions that take a SQLAlchemy `Session`, so
each one is unit-tested without Flask (`tests/`). The Flask blueprint
`src/deliver/spa_api.py` is a thin transport layer over the same functions.

---

## 2. Connect — reading the workbook honestly

**File:** `src/connect/excel_loader.py`

The approved dataset (`data/dataset/CSE_results_150_students_3_Subjects.xlsx`)
has three sheets: `Results` (one row per student per assessment, 1,650 rows),
`Assessment Map` (weight and SILOs per assessment) and `Student Summary`.
The loader exposes one `load_*()` function per target table so the parse
stage does not care which dataset shape it is reading — the same function
names exist in `historical_dataset_loader.py` for the small sample CSVs used
by the tests.

Two things worth knowing:

- `parse_silo_tags(text)` parses the workbook's `"SILO1: desc; SILO2: desc"`
  strings. It is the *one* parser for that format and is reused by the model
  stage, so the two can never drift apart. Malformed segments are skipped,
  not fatal (N5: reject the row, not the import).
- `load_topic_materials()` returns the team's **curated resource list**
  (`curated_resources.csv`) because the workbook contains no subject
  material at all. Each row is tagged `provenance=curated`; the UI labels
  it so. If the file is absent the loader returns an honest empty frame and
  the study plan says "no material yet" rather than inventing any.

`moodle_client.py` exists for the future live connection. It only ever calls
read-only web-service functions, and a test asserts that (F12).

---

## 3. Parse — validate before anything touches the database

**Files:** `src/parse/schema_validation.py`, `src/parse/cleaners.py`

Every incoming row is checked against a Pydantic model
(`AssessmentResultRecord`, `TopicMaterialRecord`, …) before it is stored.
This is where N5 — *treat imported text as untrusted* — starts: a bad row is
logged and dropped, the import continues, and a value that could hurt a
student is rejected outright (for example `source_url` must begin with
`https://`, so a link handed to a student can never be `javascript:`).

`cleaners.py` upserts on natural keys (subject code, student number, subject
+ assessment + student) so re-running the pipeline is idempotent — the live
site rebuilds its database on every boot and produces identical rows.

It also seeds two demo conveniences that a production deployment would
replace: a consent record per student (N2) and a login per student whose
password is the student number (documented as demonstration scope).

---

## 4. Model — from feedback to skill gaps, without a black box

**File:** `src/model/silo_mapping.py`

This is the "AI" the tender promised, and the most important design decision
in the codebase: **it is TF-IDF cosine similarity, not a hosted language
model.** The reasons are the promises above. A similarity score is a
reproducible number a student or marker can question; a model's paraphrase is
not. It also costs nothing and cannot hallucinate a gap that is not in the
text.

`extract_skill_gaps(session, assessment_result)` produces `SkillGap` rows
from two sources:

1. **Explicit SILO tags** on the result (`_extract_from_silo_tags`). The
   150-student workbook tags every result with the SILOs it covers, so each
   tag becomes a gap with `confidence = 1.0` (`SILO_TAG_CONFIDENCE`) and its
   `source_evidence_text` is the marker's own comment. Severity comes from the
   score band (`_severity_for_score`: under 50 high, 50–69 medium, otherwise
   low).
2. **Feedback text** (`_extract_from_feedback_text`), used when a result has
   no tags. The comment is split into clauses (`_split_into_clauses`), each
   clause is compared against the subject's learning-outcome descriptions
   with `best_similarity()` (scikit-learn TF-IDF + cosine), and a clause
   becomes a gap only above `LO_MAPPING_THRESHOLD`.

Every gap carries the exact text it came from and a confidence. Gaps below
`CONFIDENCE_REVIEW_THRESHOLD` (0.15) are never shown to a student — that is
F4's "held back until checked", enforced with a `reviewed` flag that every
student-facing query filters on.

`map_gap_to_learning_outcome()` links a gap to a `LearningOutcome`, by SILO
code when the tag gives one, otherwise by best similarity. `gap_type_for()`
classifies an outcome's wording (conceptual / procedural / applied) — the
fixed lookup that later chooses the study method (F7).

**Optional LLM path** — `src/model/ai_analysis.py`. Behind
`is_ai_enabled()`, a Gemini or Anthropic model can write a second opinion.
Two rules keep it safe: the marker feedback is fenced inside the prompt as
*data*, never as an instruction (N5), and the response must validate against
the `DiagnosticResult` Pydantic schema or it is discarded. It is never on the
critical path — see §7.

---

## 5. Estimate — the mastery number, and why it is weighted

**File:** `src/estimate/mastery.py`

`calculate_mastery_score(session, student, learning_outcome)` is the number
students see everywhere. It is built to be explainable (F6):

1. **Baseline** — the weighted mean of the student's scores on the
   assessments that *test this outcome* (`_relevant_results`: results whose
   SILO tags include the outcome; if none are tagged, all results in the
   subject). Weights are the workbook's assessment weights, so a 40%
   examination counts for more than a 15% test. This matches how the subject
   itself computes the total, which is why the dashboard can show the
   arithmetic: `(49×20% + 51×25% + 50×40%) ÷ 85% = 50.06%`.
2. **Penalty** — only gaps found in *feedback text* reduce the score
   (severity-weighted). Gaps that came from SILO tags are evidence, not a
   second penalty: the low mark already lowered the baseline, and counting it
   twice was an early defect the team fixed.
3. **Engagement bonus** — each "Mark as practised" adds
   `ENGAGEMENT_BONUS_PER_COMPLETION` (0.05), capped at
   `ENGAGEMENT_BONUS_CAP` (0.15). Small and capped by design (F11): it
   rewards doing the work without letting clicks manufacture mastery.

Every score is stored with an `explanation_text` that names the results and
gaps behind it.

`recommend_study_method()` is a fixed table keyed by gap type — a worked
example, retrieval practice or spaced practice. No model chooses it (F7).

`generate_study_material()` retrieves the closest `TopicMaterial` passage for
the outcome (tagged ones first, then subject-wide) and templates a study
prompt *from the passage's own words*. "Checked against subject materials"
(F8) is satisfied by construction: the material *is* the source, cited by
title and link. With no material the recommendation says so plainly.

**Quizzes** — `src/estimate/quiz.py` builds up to three questions per
outcome from the student's *reviewed* gaps, each grounded in the closest
passage, which the UI reveals as the model answer. Templated, therefore
never wrong; deliberately plain rather than creative.

---

## 6. Deliver — pages and JSON over the same checks

**Files:** `src/deliver/app.py`, `spa_api.py`, `dashboard_api.py`,
`insight_api.py`, `ai_insight_api.py`

Two rules apply to every request, and they are enforced *before* any row is
read, inside the framework-free functions (`dashboard_api.py`) rather than in
the routes:

- `require_student_access(actor, student_id)` (N6) — a student may only open
  their own record; the check is server-side on every page and API call, so
  changing an id in the address gives 403.
- `ensure_consent_active(session, student_id)` (N2) — no consent, no
  computation. The estimate stage also skips students without consent, so
  scores for them never exist rather than being merely hidden.

`spa_api.py` is the JSON API the React app uses. It is intentionally a thin
wrapper: the same functions, the same errors mapped to 401/403, the Flask
session cookie as the credential (same origin, so no tokens or CORS).

`insight_api.py` writes the plain-English **Insight** page from the numbers
above — headline, per-subject paragraph, weakest outcomes, the highest-weight
assessment as the lever, recurring feedback phrases with advice, and "this
week" steps. It is deterministic: same marks, same words, instantly. It
exists because the LLM page could not be relied on (free-tier quota, cold
starts), and a student should never meet an error where their summary should
be.

`ai_insight_api.py` is the optional LLM second opinion: cached 30 minutes per
student, quota and rate-limit errors turned into plain messages, and the
React page calls it only when the student presses **Ask the AI**, with a 30 s
client-side timeout.

`app.py` still renders sign-in and the original Jinja pages; signing in lands
on the React app at `/app/`, and the Jinja pages remain as a no-JavaScript
fallback.

---

## 7. Security — the cross-cutting module

**Folder:** `src/security/`

| File | What | Why |
|---|---|---|
| `authentication.py` | Salted password hashing, `authenticate_student()` | Real login, not a picker; wrong passwords rejected; every attempt audited |
| `authorization.py` | `Actor`, `Role`, `require_student_access()` | N6 — server-side, on every request |
| `consent.py` | `ensure_consent_active()`, `record_consent()` | N2 — gates computation, not just display |
| `encryption.py` | `EncryptedString` column type (Fernet), `blind_index()` | N3 — student numbers encrypted at rest; a keyed hash allows lookup without decrypting |
| `audit.py` | `log_event()` → `AuditLogEntry` (append-only by convention) | N4 — sign-ins, failures, AI calls are recorded |

The pattern to keep: a security check is a function call at the top of the
data function, raising its own error type. Routes only translate errors to
HTTP codes. Never "fix" an access problem in a template.

---

## 8. The React student app

**Folder:** `frontend/` (Vite + React 19 + TypeScript; built bundle committed
in `frontend/dist` so the Python host needs no Node)

- `src/api.ts` — typed calls to the JSON API plus the small shared maths:
  `performanceBand()` (Fail / Pass / Credit / Distinction / HD thresholds),
  `masteryBand()`, `subjectTotal()`. Keeping the thresholds here and in
  `insight_api.py` identical is a deliberate duplication; a test pins the
  backend values.
- `src/App.tsx` — four tabs (Dashboard, Results, Study, Insight) with
  sub-sections; old routes redirect so documents and videos stay valid.
- `src/pages/TodayStrip.tsx` — the ten-second view: gauge, gap to the next
  band, the lever, the first step. Computed from the Insight response.
- `src/pages/WhatIfPage.tsx` — the grade calculator. Pure client-side
  arithmetic on the recorded weights; nothing typed is sent anywhere.
- `src/index.css` — every colour is a token; the dark theme is a second
  token set applied by system preference or the header toggle.

---

## 9. Where to change things

| You want to… | Change | Then |
|---|---|---|
| Replace the curated resources with official readings | `data/dataset/curated_resources.csv` (`provenance=subject`) | re-run `python -m src.pipeline` |
| Adjust when a gap is held back | `CONFIDENCE_REVIEW_THRESHOLD` in `silo_mapping.py` | run `pytest` — tests pin the gate |
| Change the grade bands | `BANDS` in `insight_api.py` **and** `performanceBand` in `api.ts` | `test_deliver_insight_api.py` will tell you if they diverge |
| Add an API endpoint | `spa_api.py` (+ a function in `dashboard_api.py`), then `api.ts` | keep the two security calls at the top |
| Add a page | `frontend/src/pages/`, route in `App.tsx` | `cd frontend && npm run build`, commit `dist/` |

Run everything with `python -m pytest` (151 tests, about 45 s). If this
document and the code disagree, the code and its tests are right — please
fix the document.

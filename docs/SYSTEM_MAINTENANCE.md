# System Maintenance Documentation

Learning Journey Assistant (LJAS) — CSE5IDP, team IDP_OL_G9 (Jira project IOG).

Audience: whoever maintains, deploys or hands over this system. For
first-time local setup see `docs/ENVIRONMENT_SETUP.md`; for field-level
data definitions see `docs/DATA_DICTIONARY.md`. This document covers
architecture, deployment, routine operations, troubleshooting and known
limitations, and deliberately does not repeat those two.

---

## 1. What the system is

A **formative** tool: it reads a student's assessment results and rubric
feedback, works out which learning outcomes (SILOs) the lost marks map
to, and produces a private mastery dashboard, a study plan, practice
quizzes and revision material.

Two boundaries are architectural, not cosmetic, and must survive any
change:

- **F12 — read-only with respect to Moodle.** The system never writes
  back to Moodle and never alters an official grade. `src/connect/`
  only reads.
- **N2 — consent gates computation, not just display.** Students
  without active consent are skipped in the Estimate stage entirely
  (`ensure_consent_active`), so no scores are generated for them in the
  first place. Do not "fix" this by filtering at render time.

---

## 2. Architecture

A five-stage pipeline plus a web layer, all Python/Flask/SQLAlchemy.
There is **no LLM in the default path** — skill-gap extraction, SILO
mapping, mastery scoring and quiz generation all run on local TF-IDF /
cosine similarity.

```
        ┌────────────┐
Moodle  │            │   (falls back to bundled sample data
or .xlsx│  connect   │    when no credentials / dataset set)
───────▶│            │
        └─────┬──────┘
              │  raw rows
        ┌─────▼──────┐
        │   parse    │  validate, clean, upsert; seed consent + demo logins
        └─────┬──────┘
        ┌─────▼──────┐
        │   model    │  extract skill gaps, map each gap → learning outcome
        └─────┬──────┘
        ┌─────▼──────┐
        │  estimate  │  mastery scores, study recommendations, quiz questions
        └─────┬──────┘
        ┌─────▼──────┐
        │  deliver   │  Flask app: dashboard, plan, quizzes, resources,
        └────────────┘  coordinator report, opt-in AI insight
```

`security/` and `db/` are cross-cutting, used by every stage.

### 2.1 Module map (`src/`)

| Package | Responsibility | Key files |
|---|---|---|
| `connect/` | Read source data. Never writes to Moodle (F12). | `moodle_client.py` (HTTP wrapper, needs a real WS token), `excel_loader.py` (the real 150-student workbook), `historical_dataset_loader.py` (bundled synthetic CSVs) |
| `parse/` | Validate + clean + upsert into the DB; seed consent and demo credentials. Chooses the loader based on `HISTORICAL_DATASET_PATH`. | `cleaners.py`, `schema_validation.py` |
| `model/` | Skill-gap extraction and SILO mapping (TF-IDF). Optional LLM path. | `silo_mapping.py`, `ai_analysis.py` |
| `estimate/` | Weighted mastery scoring, study recommendations, grounded quiz generation. | `mastery.py`, `quiz.py` |
| `deliver/` | Flask app, routes and Jinja templates. | `app.py`, `dashboard_api.py`, `coordinator_api.py`, `ai_insight_api.py`, `templates/` |
| `security/` | Authentication, authorization, consent, encryption, audit. | `authentication.py`, `authorization.py`, `consent.py`, `encryption.py`, `audit.py` |
| `db/` | SQLAlchemy engine/session and ORM models. | `database.py`, `models.py` |
| `common/` | Logging configuration. | `logging_config.py` |
| `pipeline.py` | Runs Connect → Parse → Model → Estimate in one command. | — |

### 2.2 Routes (`src/deliver/app.py`)

| Route | Method | Access | Purpose |
|---|---|---|---|
| `/` | GET | Public | Landing page; redirects to `/dashboard` when signed in |
| `/login` | GET, POST | Public | Role-based sign-in (student / staff / admin) |
| `/logout` | GET | Any signed-in | Clears the session |
| `/dashboard` | GET | Signed-in | Mastery by SILO, per-subject overview, priority topics |
| `/plan` | GET | Signed-in † | Study plan — recommended next steps |
| `/quizzes` | GET | Signed-in † | TF-IDF-grounded practice questions |
| `/resources` | GET | Signed-in † | Revision materials |
| `/ai-insight` | GET | Signed-in † | **Opt-in** LLM analysis; off unless a provider is configured |
| `/coordinator` | GET | Staff / Admin only (N6) | Cohort report: per-subject/SILO averages, at-risk list |
| `/review` | GET | Staff / Admin only (N6) | F4 review queue: the low-confidence gaps held back from students |
| `/review/<gap_id>` | POST | Staff / Admin only (N6) | Record an approve/reject decision, optionally correcting the SILO link (F5) |
| `/practice/<recommendation_id>` | POST | Student | Marks a recommendation as practised (engagement, F11) |
| `/app/…` | GET | Public shell; data needs sign-in | The React SPA (`frontend/dist`); unknown paths fall back to `index.html` |
| `/api/session` | GET | Signed-in (401 otherwise) | Role, and the students this user may view (a student gets only themself) |
| `/api/students/<id>/dashboard` · `/results` · `/resources` | GET | Signed-in † | JSON for the SPA — same `require_student_access` + consent checks as the pages |
| `/api/recommendations/<id>/practice` | POST (JSON only) | Owner student † | SPA "Mark as practised"; JSON-only so a cross-site form cannot trigger it |

† A student sees only their own record. Staff/Admin may view a selected
student's page via the staff switcher (`_staff_switcher.html`); the check
is server-side (`abort(403)` on mismatch), and consent is re-checked on
every one of these routes — a student without active consent renders
`no_consent.html` rather than data.

The app is created by the `create_app()` factory — that is also what
gunicorn targets in production.

### 2.3 Data model

16 tables (`src/db/models.py`): `subjects`, `learning_outcomes`,
`rubrics`, `rubric_criteria`, `students`, `consent_records`,
`assessments`, `assessment_results`, `skill_gaps`, `mastery_scores`,
`topic_materials`, `study_recommendations`, `study_engagements`,
`user_credentials`, `quiz_questions`, `audit_log_entries`.

Field-level meaning is in `docs/DATA_DICTIONARY.md`.

---

## 3. Configuration

All settings come from environment variables, read in exactly one place
(`src/config.py`). **No secret is ever hardcoded (N3).**

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | No | `sqlite:///./ljas_dev.db` | Any SQLAlchemy URL; swap to Postgres by changing this alone |
| `APP_SECRET_KEY` | **Yes in any non-dev env** | `changeme-dev-only` | Flask session signing |
| `ENCRYPTION_KEY` | **Yes in any non-dev env** | a dev-only Fernet key | Generate with `Fernet.generate_key()`; see §7.1 |
| `LOG_LEVEL` | No | `INFO` | — |
| `MOODLE_BASE_URL` / `MOODLE_WS_TOKEN` | No | unset | Unset ⇒ falls back to local dataset (N9) |
| `HISTORICAL_DATASET_PATH` | No | unset | Unset ⇒ bundled synthetic CSVs. **Never set this in the demo deploy** |
| `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_MODEL` | No | unset | Unset ⇒ TF-IDF only, `/ai-insight` disabled. See §6 |

The "unset means fall back" pattern is intentional and consistent: a
fresh clone, CI and the demo deploy all run with zero configuration.

---

## 4. Deployment (Render)

Defined as infrastructure-as-code in `render.yaml`.

- **Service:** `learning-journey-assistant-demo`, Python, **free plan**.
- **Build:** `pip install -r requirements.txt`, then `npm ci && npm run build`
  in `frontend/` for the SPA. The Node step is allowed to fail without
  failing the deploy — `/app/` then reports "not built" and the Flask
  pages are unaffected.
- **Local SPA development:** run the Flask app on `:5000`, then
  `npm run dev` in `frontend/`; Vite proxies `/api`, `/login` and
  `/logout` so the session cookie stays same-origin.
- **Start:** `python -m src.pipeline && gunicorn 'src.deliver.app:create_app()' --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
- **Auto-deploys from `main`.** Live URL:
  <https://learning-journey-assistant.onrender.com>

### 4.1 The stateless-by-design decision

The start command **re-runs the whole pipeline on every boot**, so the
SQLite file is rebuilt from the bundled sample CSVs each time the
instance wakes. Consequences to understand before changing anything:

- No persistent disk is needed, and **no real student data ever touches
  the service** — `HISTORICAL_DATASET_PATH` is deliberately omitted.
- **Any runtime state is lost on restart** (engagement marks, changed
  passwords). This is acceptable for a demo and is the reason no backup
  job exists (§8).
- Boot is slower because the pipeline runs first. Combined with free-tier
  spin-down, a cold request can take **50+ seconds**.

`APP_SECRET_KEY` and `ENCRYPTION_KEY` are declared `sync: false`, meaning
their values are entered in the Render dashboard and never committed.

### 4.2 Deploying a change

1. Merge to `main` → Render auto-deploys.
2. Watch the deploy log for `Build failed` and for the pipeline's
   `Parse/Model/Estimate stage complete` lines.
3. Smoke-test: load `/`, sign in, check `/dashboard` renders scores.

If the live site serves stale code, see §9.

---

## 5. Routine maintenance

| Task | Command / action | When |
|---|---|---|
| Run the full test suite | `pytest` | Before every PR |
| Lint | `ruff check .` | Before every PR |
| Refresh scores locally | `python -m src.pipeline` | After changing data or scoring logic |
| Run the app locally | `python -m src.deliver.app` → `localhost:5000` | Development |
| Review dependencies | `requirements.txt` | Each sprint |

Tests use a separate `ljas_test.db`, so they never touch your dev
database. The pipeline is **idempotent** — re-running it does not
duplicate gaps (it skips results that already have them) and does not
reset a password that has since been changed.

---

## 6. The optional AI (LLM) path

Default is **off**, and off is the documented, defensible position: the
tender committed to an explainable, no-hallucination, $0 approach.

- With `LLM_PROVIDER` / `LLM_API_KEY` unset, `src/model/ai_analysis.py`
  raises `AIAnalysisUnavailable` and every caller falls back to TF-IDF.
  `/ai-insight` stays disabled.

**Supported providers.** `analyze_student` dispatches on `LLM_PROVIDER`
across `SUPPORTED_PROVIDERS`. Having two, not one, is the tender's
Section 8 risk-7 mitigation in practice — no single vendor's cost,
downtime or policy change can remove the LLM path, and switching is one
environment variable with no caller change.

| `LLM_PROVIDER` | Key from | Default model | Extra install | Cost |
|---|---|---|---|---|
| `gemini` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | `gemini-flash-latest` | none — REST via `requests` | free tier |
| `anthropic` | [console.anthropic.com](https://console.anthropic.com) | `claude-sonnet-4-5` | `pip install anthropic` | paid / trial credit |

`gemini` is the recommended default for this project: it needs no extra
dependency on the free-tier host and no spend, which is what the tender
budgeted for (Section 7, "Free tier / trial credits (est. $0)").
Credentials travel in the `x-goog-api-key` header, never in the URL, so
they cannot surface in request logs (N3).
- Feedback text is treated as **untrusted input (N5)** — it is fenced in
  `<untrusted_data>` tags and never interpreted as instructions. Keep
  that fencing if you touch the prompt.
- Responses are validated against a pydantic `DiagnosticResult` before
  use.

**Before enabling it:** turning this on sends student feedback text to an
external API on every analysis. Confirm consent (N2) and cost first, and
set the key in the Render dashboard, never in the repo.

---

## 6a. The skill-gap review gate (F4, F5)

F4 requires that low-confidence gaps are "held for review and are not
shown to the student **until checked**". Checked by a person — which is
what `/review` provides.

**How a gap moves.** `SkillGap.review_status` carries the state:

| Status | Set by | Visible to student? |
|---|---|---|
| `auto_approved` | extraction, confidence ≥ `CONFIDENCE_REVIEW_THRESHOLD` (0.15) | yes |
| `pending` | extraction, confidence < threshold | no — sits in `/review` |
| `approved` | a Staff/Admin reviewer | yes |
| `rejected` | a Staff/Admin reviewer | no, and leaves the queue |

`reviewed` (bool) stays the single flag every student-facing query
filters on; `review_status` is what makes the *gate* auditable.

**Why both columns exist.** `reviewed=False` alone means two different
things — "nobody has looked at this" and "a human looked and rejected
it" — so a rejected gap would reappear in the queue for ever. It is worth
knowing the history here: before this feature, `reviewed` was set once at
extraction time by the confidence comparison and never changed again. The
field was named `reviewed`, so the code read as compliant, but no human
ever reviewed anything and nothing below the threshold could ever reach a
student. A threshold is triage, not a review.

**F5.** `review_gap()` accepts a `learning_outcome_id`, so a reviewer can
correct a wrong gap→SILO link while deciding. The outcome must belong to
the subject the result was assessed under — staff correct links, they
don't invent cross-subject ones.

**N4.** Every decision writes an append-only audit row
(`skill_gap_approved` / `skill_gap_rejected`) naming the gap and, when the
link changed, the `silo:<from>-><to>` correction — so the review history
is reconstructable from the audit log alone.

---

## 7. Security operations

Implemented in `src/security/`, covered by `tests/test_security.py` and
`tests/test_security_authentication.py`.

- **Authentication** — salted PBKDF2 hashes via werkzeug; no plaintext
  passwords stored. Every attempt, success or failure, is audit-logged
  (`sign_in` / `sign_in_failed`, N4).
- **Authorization** — server-side role checks (N6). `/coordinator` and
  `/review` are Staff/Admin only; never rely on hiding a link in a
  template. `tests/test_deliver_app.py` covers the case that actually
  matters: a student POSTing straight at `/review/<gap_id>` gets 403 and
  the gap does not move.
- **Consent** — `ensure_consent_active` gates the Estimate stage (N2).
- **Encryption at rest** — Fernet (N3).
- **Audit log** — append-only `audit_log_entries` (N4).

### 7.1 Rotating `ENCRYPTION_KEY`

The default in `config.py` is a real but **public, dev-only** Fernet key.
Any non-dev environment must set its own. Because the demo rebuilds its
database from source CSVs on every boot, rotation there is simply:
generate a new key, update it in the Render dashboard, redeploy. In an
environment with persisted encrypted data, you would need to decrypt
with the old key and re-encrypt with the new one before rotating —
no such environment exists today.

### 7.2 Account model — scope limit

Seeded demo accounts have fixed, documented passwords
(`docs/ENVIRONMENT_SETUP.md`). There is no self-service sign-up and no
password reset. The *mechanism* is real; the *account management around
it* is demonstration-scope. State it that way in any hand-over.

---

## 8. Backup and recovery

There is **no backup job, by design**. The demo database is derived
data — it is regenerated from version-controlled sample CSVs on every
boot, so the recovery procedure is "redeploy".

This changes the moment the system is pointed at real data or a
persistent database. Before that happens, someone must add: scheduled
backups of the datastore, a documented restore test, and a retention
period agreed with the data owner.

Real student records are **never** committed — `data/provided/` is
gitignored (N3).

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| First request takes ~50s | Free-tier instance spun down, then the pipeline runs at boot | Expected. Warm it before a demo by loading the site a minute early |
| Live site serves old code / a route 404s | Render not deploying `main` | Settings → Build & Deploy: Branch = `main`, Auto-Deploy = Yes, then Manual Deploy → **Clear build cache & deploy** |
| `/ai-insight` returns 404 or is disabled | No LLM provider configured (the default) | Expected. See §6 |
| Dashboard renders but all scores are empty | Pipeline hasn't run, or the student has no active consent | Run `python -m src.pipeline`; check `consent_records` (N2 skips by design) |
| Login always rejected | Wrong role radio selected, or password changed since seeding | Students sign in with their student number; see the demo table in `ENVIRONMENT_SETUP.md` |
| Tests pass locally, deploy fails | A dependency missing from `requirements.txt` | Add it; the build installs only from that file |
| `git` fails on long paths (Windows) | OneDrive path depth | Clone to a short path (e.g. `C:\lja-repo`) and `git config core.longpaths true` |

Logs: Render dashboard → the service → Logs. Locally, `LOG_LEVEL=DEBUG`.

---

## 10. Known limitations

Carried openly rather than hidden — each is flagged on its Jira ticket.

1. **Flask, not FastAPI.** IOG-34's spec mentions FastAPI compatibility;
   what is built and running is Flask. Flagged on the ticket.
2. **`rubric_criteria.learning_outcome_id` is NULL on all rows.** The
   SILO/rubric match is therefore text-based, not a SQL join. Populating
   this FK is the single highest-value correctness improvement left, but
   it needs a confirmed mapping rule — do not guess at it.
3. **Two front ends over one backend.** The server-rendered Flask pages
   are the complete product (they include the staff pages). The React SPA
   at `/app/` covers the three student views — dashboard, results, study
   plan — over the JSON API in `src/deliver/spa_api.py`. It has no
   staff/review screens; staff use the Flask pages.
4. **Demo-scope account management** — see §7.2.
5. **Free-tier deployment** — cold starts, ephemeral storage (§4.1).
6. **Moodle integration is untested against a live instance** — the HTTP
   client is real but has never run against a real WS token.

---

## 11. Hand-over checklist

- [ ] `APP_SECRET_KEY` and `ENCRYPTION_KEY` set to fresh values in the
      target environment (never the committed dev defaults)
- [ ] `HISTORICAL_DATASET_PATH` left unset unless the environment is
      cleared for real student data
- [ ] `pytest` and `ruff check .` pass on `main`
- [ ] Deploy branch confirmed as `main` with auto-deploy on
- [ ] Backup/retention agreed **before** any real data is loaded (§8)
- [ ] Limitations in §10 read and accepted by the receiving party

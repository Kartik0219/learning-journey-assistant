# Environment Setup

Covers N8 ("Supply setup instructions...") and IOG-32 ("Configure
development environment"). For a beginner-friendly, click-by-click version
of this same setup, see `docs/RUN_IN_VSCODE.md`.

## Prerequisites

- Python 3.11+
- `pip`

## Setup

```bash
git clone <this repo's URL>
cd learning-journey-assistant
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # then fill in real values if you have them
```

Nothing in `.env` is required to get started - the defaults point at a
local SQLite file and the pipeline falls back to the bundled synthetic
sample data (`data/sample/`) when Moodle credentials aren't set (N9).

## Running the pipeline

```bash
python -m src.pipeline
```

This runs all four data stages end to end against `ljas_dev.db` (a local
SQLite file, gitignored): Connect + Parse (sample dataset -> validated,
cleaned rows), Model (skill-gap extraction + SILO mapping), and Estimate
(mastery scoring + study recommendations, skipping any student without
active consent). You should see log lines like:

```
Parse stage complete: 1 subjects, 3 learning outcomes, 4 rubric criteria, 3 students, 3 assessment results, 6 topic materials
Model stage complete: 3 skill gap(s) extracted, 3 mapped to a learning outcome.
Estimate stage complete: 9 mastery score(s), 9 study recommendation(s).
```

`python -m src.parse.cleaners` still works on its own if you only want
Connect + Parse (e.g. to inspect the raw imported data before Model/
Estimate touch it).

## Running against the real provided dataset (IOG-33)

By default the pipeline runs against the synthetic sample CSVs above -
nothing extra to configure. To run it against the subject's anonymised
`CSE_results_150_students_3_Subjects.xlsx` workbook instead (150
students, 3 subjects, 1,650 assessment results) - the same data the live
demo uses:

```bash
# The workbook is in the repo at data/dataset/ - the subject coordinator
# approved publishing it in this repository and on the live demo (13 Sep 2026).
export HISTORICAL_DATASET_PATH=data/dataset/CSE_results_150_students_3_Subjects.xlsx
python -m src.pipeline       # about 2 minutes
```

`data/provided/` stays gitignored for any data that is *not* approved for
publication.

`src.parse.cleaners.run_parse_stage()` picks `src.connect.excel_loader`
over the synthetic-CSV loader automatically whenever
`HISTORICAL_DATASET_PATH` is set (same unset-means-fallback pattern as
Moodle) - nothing else needs to change. Skill-gap extraction
(`src.model.silo_mapping`) also switches per-result to using the
workbook's explicit SILO tags and score-band severity instead of the
feedback-text heuristic - see `docs/DATA_DICTIONARY.md`'s
`assessment_results` / `skill_gaps` sections for the full field-level
detail. At full scale this extracts 3,607 skill gaps across the 1,650
results, all mapped to a learning outcome, and 1,950 mastery scores. Each
outcome's mastery is the weight-averaged score of the results tagged with
it, using the workbook's `Weight` column.

## Running the dashboard

```bash
python -m src.deliver.app
```

Then open `http://localhost:5000` and log in with a real password (see
"Demo accounts" below) — see `src.security.authentication`'s docstring
for how the check works (salted hashes, no plaintext passwords stored);
everything downstream of login (authorization, consent gating) is the
same real, tested IOG-42 security layer as before. Run the pipeline
first so there's mastery data to show; re-run it any time to refresh
scores without restarting the server.

Once signed in, the **Results** tab shows every assessment result as a
table (Assessment Type, Score, Feedback Comment, SILOs, Weight, Weighted
Score) — see `docs/USER_GUIDE.md` §3.2 for the student-facing walkthrough
of this and every other page.

### Demo accounts

Seeded automatically by `seed_demo_credentials` every time the pipeline's
Parse stage runs (`src.parse.cleaners`), idempotently - re-running the
pipeline never resets a password you've since changed.

| Dataset | Student number | Password |
|---|---|---|
| Sample CSVs (default) | `DEMO0001` … `DEMO0018` | same as the student number |
| 150-student workbook (live demo) | `STU0001` … `STU0150` | same as the student number |

The app is **student-only**: the Staff and Admin roles, the coordinator
report and the skill-gap review queue were removed on 13 Sep 2026 at the
team's request.

Fixed and documented on purpose - this remains an academic
demonstration with no self-service sign-up, not a claim of
production-grade credential management. The *mechanism* is real: a
wrong password is genuinely rejected (`src.security.authentication.
AuthenticationError`), and every sign-in attempt (success or failure) is
audit-logged (`sign_in` / `sign_in_failed`, N4).

## New in the app-build phase

Five tickets added on top of the pipeline above, each owned by one group
member (IOG-45 through IOG-49) — the underlying Python/SQLAlchemy/
Flask/TF-IDF stack is unchanged, no new database engine, no LLM:

- **Real password authentication** (`src.security.authentication`,
  IOG-47, Farshad) — replaces the old student/role picker. Salted
  PBKDF2 hashes (werkzeug's `generate_password_hash`, already a Flask
  dependency, so no new package), verified on every login, wrong
  passwords rejected, every attempt audit-logged.
- **TF-IDF quiz generation** (`src.estimate.quiz`, IOG-48, Prabhashi) —
  F8's previously unbuilt "generate a practice quiz" item. One grounded
  question per reviewed skill gap, templated from that gap's own
  verbatim evidence plus the closest topic-material passage (same
  TF-IDF cosine-similarity retrieval `src.model.silo_mapping` and
  `src.estimate.mastery` already use) — no LLM, nothing a model could
  have hallucinated. Runs as part of `run_estimate_stage` in the
  pipeline; shown under "Practice quiz" on each outcome's dashboard
  card.
- **Coordinator report** (IOG-46, Ge Su) — a Staff/Admin cohort-level
  view of per-SILO mastery and an at-risk list. Built and tested in this
  phase, then **removed on 13 Sep 2026** when the team made the app
  student-only.
- **Dashboard frontend polish** (IOG-45, Anjan) — a per-subject mastery
  overview strip above the per-SILO detail (useful once a student spans
  more than one subject, as the real dataset's students do),
  mobile-responsive layout (`base.html`'s new media query), and styled
  form inputs across the login and student pages.
- **Integration, regression testing, docs and GitHub/Jira upkeep**
  (IOG-49, Kartik) — wiring the four features above together, running
  the full test suite against them, keeping this document and the
  data dictionary accurate, and pushing/tracking the work in GitHub and
  Jira.

## Running tests

```bash
pytest
```

Tests use a separate `ljas_test.db` file so they never touch your local
dev database.

## Linting

```bash
ruff check .
```

## What's implemented vs. stubbed

| Stage | Status | Owner ticket(s) |
|---|---|---|
| Connect | Sample-CSV loader and the real-dataset Excel loader (`src.connect.excel_loader`, IOG-33) both work; Moodle client is a real HTTP wrapper but needs a real WS token to test against | IOG-33 |
| Parse | Working - validates + upserts subjects, learning outcomes, rubric criteria, students, assessment results, topic materials; seeds demo consent; picks the sample or real-dataset loader per `HISTORICAL_DATASET_PATH` | IOG-34 |
| Model (skill-gap extraction, SILO mapping) | Working - two extraction paths (explicit SILO tags + score-band severity for the real dataset; the original TF-IDF/keyword heuristic for the sample dataset, unchanged), plus an opt-in LLM path (`src.model.gap_extraction`, IOG-37) that cites a source quote and falls back to TF-IDF if the provider is down | IOG-37, IOG-38 |
| Estimate (mastery scoring, study recommendations, quiz generation, engagement) | Working - explainable weighted scoring, fixed-table study method (F7), grounded study material (F8/F9), TF-IDF-grounded quiz questions (`src/estimate/quiz.py`, F8), engagement feedback (F11) | IOG-38, IOG-39, IOG-48 (Prabhashi) |
| Deliver (student pages) | Working - real Flask app (`python -m src.deliver.app`) showing each student's mastery, results, study plan, quiz questions, resources and optional AI insight, behind the real IOG-42 security checks. Student-only since 13 Sep 2026 (the coordinator report and review queue were removed) | IOG-40, IOG-46 (Ge Su) |
| Security (encryption, RBAC, audit log, consent, authentication) | Implemented as reusable primitives in `src/security/`, wired end-to-end through the dashboard/Estimate stage above; real password authentication (`src/security/authentication.py`) replaced the old demo picker | IOG-42, IOG-47 (Farshad) |
| Frontend polish (dashboard/login styling, responsive layout, per-subject overview) | Working - see `src/deliver/templates/` | IOG-45 (Anjan) |
| Integration, regression testing, docs, GitHub/Jira upkeep | Working - full test suite passing across all app-build features, docs cross-checked, tickets/board kept current | IOG-49 (Kartik) |

Run `python -m src.pipeline` to execute Connect through Estimate in one
command, then `python -m src.deliver.app` for the dashboard - see
"Running the pipeline" / "Running the dashboard" above.

## Data fields and security controls (N8)

See `docs/DATA_DICTIONARY.md` for the field-by-field notes. Encryption
at rest, an authorization check, audit logging, and consent gating are
implemented in `src/security/` (IOG-42), wired into the Estimate stage
and the dashboard, and covered by `tests/test_security.py`,
`tests/test_estimate_mastery.py`, and `tests/test_deliver_dashboard.py`.
Real password/credential authentication (`src/security/authentication.py`,
IOG-47) is also implemented and wired into `src.deliver.app`'s login -
what's still demonstration-scope is the account model around it: seeded
accounts have fixed, documented passwords (see "Demo accounts" above),
with no self-service sign-up or password-reset flow, not a claim of
production-grade identity management. Generate your own `ENCRYPTION_KEY`
before running anything beyond local dev - see `.env.example`.

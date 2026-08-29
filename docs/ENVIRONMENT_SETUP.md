# Environment Setup

Covers N8 ("Supply setup instructions...") and IOG-32 ("Configure
development environment").

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
nothing extra to configure. To run it against the real provided
`CSE_results_150_students_3_Subjects.xlsx` workbook instead (150
students, 3 subjects, 1,650 assessment results):

```bash
# Real student records must never be committed (N3) - data/provided/ is
# gitignored. Put the file there yourself; it isn't in the repo.
mkdir -p data/provided
cp /path/to/CSE_results_150_students_3_Subjects.xlsx data/provided/

export HISTORICAL_DATASET_PATH=data/provided/CSE_results_150_students_3_Subjects.xlsx
python -m src.pipeline
```

`src.parse.cleaners.run_parse_stage()` picks `src.connect.excel_loader`
over the synthetic-CSV loader automatically whenever
`HISTORICAL_DATASET_PATH` is set (same unset-means-fallback pattern as
Moodle) - nothing else needs to change. Skill-gap extraction
(`src.model.silo_mapping`) also switches per-result to using the
workbook's explicit SILO tags and score-band severity instead of the
feedback-text heuristic - see `docs/DATA_DICTIONARY.md`'s
`assessment_results` / `skill_gaps` sections for the full field-level
detail. At full scale this currently extracts ~3,600 skill gaps across
the 1,650 results, all mapped to a learning outcome.

**Open:** whether this xlsx is tutor-issued or team-generated is not
yet confirmed (Ge Su, IOG-33) - see that ticket's comments. Not
blocking on it, but it needs to be stated accurately in the final
report once confirmed.

## Running the dashboard

```bash
python -m src.deliver.app
```

Then open `http://localhost:5000` and pick a demo student (or Staff/
Admin) on the login screen — see `src.deliver.app`'s docstring for why
this login is demonstration-level only (no password), not a real
authentication system; everything downstream of it (authorization,
consent gating) is the real, tested IOG-42 security layer. Run the
pipeline first so there's mastery data to show; re-run it any time to
refresh scores without restarting the server.

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
| Model (skill-gap extraction, SILO mapping) | Working - two extraction paths (explicit SILO tags + score-band severity for the real dataset; the original TF-IDF/keyword heuristic for the sample dataset, unchanged), see `src/model/silo_mapping.py`'s docstring | IOG-37, IOG-38 |
| Estimate (mastery scoring, study recommendations, engagement) | Working - explainable weighted scoring, fixed-table study method (F7), grounded study material (F8/F9), engagement feedback (F11). Quiz generation (also part of F8) is not yet built. | IOG-38, IOG-39 |
| Deliver (dashboard) | Working - real Flask app (`python -m src.deliver.app`) showing mastery, gaps, and recommendations per student, behind the real IOG-42 security checks | IOG-40 |
| Security (encryption, RBAC, audit log, consent) | Implemented as reusable primitives in `src/security/`, and wired end-to-end through the dashboard/Estimate stage above | IOG-42 |

Run `python -m src.pipeline` to execute Connect through Estimate in one
command, then `python -m src.deliver.app` for the dashboard - see
"Running the pipeline" / "Running the dashboard" above.

## Data fields and security controls (N8)

See `docs/DATA_DICTIONARY.md` for the field-by-field notes. Encryption
at rest, an authorization check, audit logging, and consent gating are
implemented in `src/security/` (IOG-42), wired into the Estimate stage
and the dashboard, and covered by `tests/test_security.py`,
`tests/test_estimate_mastery.py`, and `tests/test_deliver_dashboard.py`.
What's *not* done yet: real password/credential authentication - the
dashboard's login (`src.deliver.app`) is an explicitly-disclosed,
demonstration-level session (pick a demo student/role, no password),
not a production auth system. Generate your own `ENCRYPTION_KEY` before
running anything beyond local dev - see `.env.example`.

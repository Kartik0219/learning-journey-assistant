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
python -m src.parse.cleaners
```

This loads the sample dataset (Connect stage), validates and cleans it
(Parse stage), and writes it into `ljas_dev.db` (a local SQLite file,
gitignored). You should see a log line like:

```
Parse stage complete: 1 subjects, 3 learning outcomes, 4 rubric criteria, 3 students
```

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
| Connect | Historical dataset loader works; Moodle client is a real HTTP wrapper but needs a real WS token to test against | IOG-33 |
| Parse | Working - validates + upserts subjects, learning outcomes, rubric criteria, students | IOG-34 |
| Model (skill-gap extraction, SILO mapping) | Stub, raises `NotImplementedError` | IOG-37, IOG-38 |
| Estimate (mastery scoring, study recommendations, quizzes) | Stub | IOG-38, IOG-39 |
| Deliver (dashboard) | Stub, but gated by real IOG-42 security checks (see below) | IOG-40 |
| Security (encryption, RBAC, audit log, consent) | Implemented as reusable primitives in `src/security/` | IOG-42 |

## Data fields and security controls (N8)

See `docs/DATA_DICTIONARY.md` for the field-by-field notes. Encryption
at rest, an authorization check, audit logging, and consent gating are
implemented in `src/security/` (IOG-42) and covered by
`tests/test_security.py`. What's *not* done yet: there's no login/
session system for these primitives to sit behind (that's Phase 4/6,
IOG-40) - `Actor` is constructed directly in code/tests for now rather
than derived from a real request. Generate your own `ENCRYPTION_KEY`
before running anything beyond local dev - see `.env.example`.

# Learning Journey Assistant

AI-powered formative learning assistant that turns LMS assessment data — marks, rubrics, instructor feedback, and Subject Intended Learning Outcomes (SILOs) — into an interactive, evidence-backed competency dashboard with targeted study pathways.

> **Formative by design.** Diagnostic scores are coaching tools only. The system has no write path to official instructor grades.

## Live Demo

**[https://learning-journey-assistant.onrender.com](https://learning-journey-assistant.onrender.com)**

Deployed on Render's free tier, so the instance spins down after inactivity — the first request can take 50+ seconds to respond. Sign in as **STU0001 / STU0001** (any student number from STU0001 to STU0150 — the password is the student number). The demo runs on the subject's anonymised 150-student dataset (`data/dataset/`), approved for publication by the subject coordinator. The app is student-only.

## Overview

Valuable academic data currently sits isolated in the LMS (Moodle), leaving students unsure how to turn feedback into a concrete improvement plan. Learning Journey Assistant securely connects subject descriptions, rubrics, and grade results to continuously evaluate a student's performance against learning outcomes — diagnosing the specific skills behind lost marks, and converting them into prioritised, evidence-backed study steps.

## How It Works

1. **Ingest** — Assessment structure (rubric criteria, weights, SILO mappings) and student performance data (marks, qualitative instructor feedback) are imported through the instructor data-input view.
2. **Diagnose** — The AI diagnostic engine maps each performance record directly to course Learning Outcomes, extracting literal evidence quotes from instructor feedback and computing a weighted mastery estimate per outcome.
3. **Coach** — The student dashboard presents mastery tiers, the evidence behind every rating, and a prioritised study plan with recommended course modules and resources.

## Core Features

### Student Dashboard
- **Visual Competency Tracker** — progress bars for each Learning Outcome, categorised as *Mastered*, *On Track*, or *Focus Area*.
- **Evidence Cards** — the exact instructor feedback quotes that justify why an outcome was rated a *Focus Area*, with the source assessment and a confidence indicator. No rating without evidence.
- **Actionable Next Steps** — a prioritised list of concrete study steps and recommended course modules/resources addressing the identified gaps.
- **Formative Notice** — a clear, persistent disclaimer that diagnostic scores are coaching tools and do not alter official instructor grades.
- **Adaptive Practice Quizzes** — generated against the student's weakest outcomes.

### Results
- **Every assessment in one place** — each subject's assessments with type, score, marker feedback, the SILOs covered, weight and weighted score, plus the subject's weighted total.

### AI Diagnostic Engine
- LLM processing pipeline with a **structured system prompt** and **strict JSON schema enforcement** — malformed output is rejected and retried, never rendered.
- Accepts three inputs: **Subject Data** (LOs, modules), **Assessment Data** (rubric criteria, weights), and **Student Performance Data** (marks, instructor feedback text).
- Produces structured JSON mapping student performance to course LOs, with evidence quotes, severity, and targeted recommendations.
- **Built-in guardrails against hallucination** — evidence is extracted only from the literal rubric/feedback text, never invented — and data-privacy protections.

## Roadmap

- Longitudinal tracking across entire degrees
- Mapping competencies to employability frameworks
- Early-risk analytics for educators
- Reflective AI dialogue
- Gamified milestones

## Run It Yourself

New here? Follow **[Run the app in Visual Studio Code](docs/RUN_IN_VSCODE.md)** — download the code, install it and open the app in about 10 minutes, no prior setup needed.

Quick version, once Python 3.11+ is installed:

```bash
git clone https://github.com/Kartik0219/learning-journey-assistant.git
cd learning-journey-assistant
python -m venv .venv
.venv\Scripts\activate          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m src.pipeline
python -m src.deliver.app       # then open http://127.0.0.1:5000  (DEMO0001 / DEMO0001)
```

## Documentation

| Document | For |
|---|---|
| [Run in VS Code](docs/RUN_IN_VSCODE.md) | Step-by-step: download and run the app on your own computer |
| [User Guide](docs/USER_GUIDE.md) | Students using the app |
| [System Maintenance](docs/SYSTEM_MAINTENANCE.md) | Architecture, deployment, operations, troubleshooting, known limitations |
| [Environment Setup](docs/ENVIRONMENT_SETUP.md) | Running it locally for the first time |
| [Data Dictionary](docs/DATA_DICTIONARY.md) | Field-by-field data definitions |
| [Tender Document](docs/TENDER_DOCUMENT.md) | Original project proposal |

## Project Structure

- `docs/` — project documentation: tender document, reports, and diagrams
- `src/` — application source code
- `tests/` — automated tests

## Subject

Developed for **CSE5IDP: Industry Development Project**, La Trobe University.

# Learning Journey Assistant

AI-powered formative learning assistant that turns LMS assessment data — marks, rubrics, instructor feedback, and Subject Intended Learning Outcomes (SILOs) — into an interactive, evidence-backed competency dashboard with targeted study pathways.

> **Formative by design.** Diagnostic scores are coaching tools only. The system has no write path to official instructor grades.

## Live Demo

**[https://learning-journey-assistant.onrender.com](https://learning-journey-assistant.onrender.com)**

Deployed on Render's free tier, so the instance spins down after inactivity — the first request can take 50+ seconds to respond. Demo sign-in accounts and passwords are documented in `docs/ENVIRONMENT_SETUP.md`. This demo runs only against the bundled synthetic sample dataset (see `render.yaml`), never real student data.

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

### Instructor / Data-Input View
- Form-based submission of student assignment feedback, rubric scores, and course Learning Outcomes to trigger the AI diagnostic pipeline.
- Review and confirmation of low-confidence diagnostic items before they reach the student view.

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

## Documentation

| Document | For |
|---|---|
| [User Guide](docs/USER_GUIDE.md) | Students and teaching staff using the app |
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

# Learning Journey Assistant
AI-powered formative tool that bridges the gap between student assessment feedback and academic improvement.
## Live Demo

**[https://learning-journey-assistant.onrender.com](https://learning-journey-assistant.onrender.com)**

Deployed on Render's free tier, so the instance spins down after inactivity — the first request can take 50+ seconds to respond. Demo sign-in accounts and passwords are documented in `docs/ENVIRONMENT_SETUP.md`. This demo runs only against the bundled synthetic sample dataset (see `render.yaml`), never the real student data.

## Overview
Valuable academic data currently sits isolated in Moodle, leaving students unsure how to turn feedback into a concrete improvement plan. Learning Journey Assistant securely connects subject descriptions, rubrics, and grade results to continuously evaluate a student's performance against learning outcomes, without altering official grades.
## Core Features
Automatically detects the specific skills behind lost marks. Recommends tailored study strategies. Generates adaptive practice quizzes. Directs learners to targeted revision materials. Provides a private, formative mastery dashboard showing overall mastery percentage and priority focus areas. Includes built-in guardrails to prevent AI hallucinations and protect data privacy.
## Roadmap
Longitudinal tracking across entire degrees. Mapping competencies to employability frameworks. Early-risk analytics for educators. Reflective AI dialogue. Gamified milestones.
## Run it yourself

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
| [User Guide](docs/USER_GUIDE.md) | Students and teaching staff using the app |
| [System Maintenance](docs/SYSTEM_MAINTENANCE.md) | Architecture, deployment, operations, troubleshooting, known limitations |
| [Environment Setup](docs/ENVIRONMENT_SETUP.md) | Running it locally for the first time |
| [Data Dictionary](docs/DATA_DICTIONARY.md) | Field-by-field data definitions |
| [Tender Document](docs/TENDER_DOCUMENT.md) | Original project proposal |

## Project Structure
docs contains project documentation such as the tender document, reports, and diagrams. src contains the application source code. tests contains automated tests.
## Subject
Developed for CSE5IDP: Industry Development Project, La Trobe University.

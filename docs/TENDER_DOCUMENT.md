# Tender Document – Learning Journey Assistant

This is a working draft of the tender document for Assessment 2 (CSE5IDP), built from the project description and the required tender template structure. Sections marked PLACEHOLDER need real information from the team before submission and must not be left as-is.

## 1. Tenderer Details

Team / business legal name: PLACEHOLDER
ABN or ACN: PLACEHOLDER
Business address: PLACEHOLDER
Contact person: PLACEHOLDER
Contact email: PLACEHOLDER
Contact phone: PLACEHOLDER
RFT number: PLACEHOLDER (confirm with subject coordinator)

## 2. Statement of Work

### 2.1 Project Purpose, Business Context and Objectives

The Learning Journey Assistant is an AI-powered formative tool designed to bridge the gap between student assessment feedback and actual academic improvement. Currently, valuable academic data sits isolated in Moodle, leaving students unsure how to turn feedback into a concrete plan. The objective of this project is to securely connect subject descriptions, rubrics, and grade results so that a student's performance against learning outcomes can be continuously evaluated, without altering any official grades.

### 2.2 Situation Assessment and Problem Statement

Students routinely receive marked assignments and rubric feedback but lack a structured way to translate that feedback into targeted revision. The underlying skills behind lost marks are rarely made explicit, so students often repeat the same mistakes across assessments. This project addresses that gap by automatically detecting the specific skills behind lost marks and connecting students to tailored study strategies and revision materials.

### 2.3 Options Considered and Justification

Manual academic advising and generic study guides were considered as alternatives, but neither scales across a cohort or ties recommendations directly to a student's own rubric results. An AI-assisted system that reads existing subject descriptions, rubrics, and grades was chosen because it can generate personalised, evidence-based recommendations at scale while keeping the official grade record untouched.

### 2.4 Scope of Work and Implementation Strategy

The system will ingest subject descriptions, rubrics, and grade results, map lost marks to specific learning outcomes and skills, recommend tailored study strategies, generate adaptive practice quizzes, and direct learners to targeted revision materials. Students will track progress through a private, formative mastery dashboard showing overall mastery percentages and priority focus areas. The platform will be built with strict guardrails to prevent hallucinated feedback and to maintain data privacy throughout.

### 2.5 Project Complexity, Feasibility and Recommendations

The core technical challenges are reliably mapping rubric criteria to learning outcomes, generating quiz content that is accurate and non-hallucinated, and handling student data securely. The team recommends an incremental build: start with rubric-to-outcome mapping and the mastery dashboard, then layer in adaptive quiz generation and recommendation features once the core pipeline is validated.

## 3. Constraints, Risks and Limitations

### 3.1 Constraints and Assumptions

Constraints include reliance on Moodle data access and permissions, handling of personally identifiable student information, and the tooling and hosting available to the team within the subject timeframe. It is assumed that subject rubrics and grade data are available in a structured, machine-readable format, and that the system will never write back to or alter official grades.

### 3.2 Risks and Limitations

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| AI-generated feedback is inaccurate or hallucinated | Medium | High | Guardrails, rubric-grounded prompts, and human-reviewable output |
| Student data privacy is compromised | Low | High | Data minimisation, access controls, no third-party data sharing |
| Integration with Moodle data is delayed or restricted | Medium | Medium | Use sample/exported data as a fallback during development |
| Team time constraints affect delivery | Medium | Medium | Incremental scope, prioritise core mastery dashboard first |

## 4. Evaluation Criteria and Requirements

| Criterion | Weighting | Description |
| --- | --- | --- |
| Project Summary | PLACEHOLDER % | Clarity and completeness of purpose, objectives, and context |
| Business Assessment | PLACEHOLDER % | Quality of situation assessment, options, and justification |
| Project Scope | PLACEHOLDER % | Feasibility and completeness of scope and implementation strategy |
| Evaluation Matrix, Metrics and Deliverables | PLACEHOLDER % | Clarity of deliverables, timelines, and success metrics |

| Requirement | Type | Importance |
| --- | --- | --- |
| Map rubric criteria to learning outcomes | Functional | High |
| Generate adaptive practice quizzes | Functional | High |
| Formative mastery dashboard | Functional | High |
| Prevent hallucinated feedback | Non-functional | High |
| Protect student data privacy | Non-functional | High |
| No alteration of official grades | Non-functional | High |

## 5. Deliverables and Anticipated Hours and Timelines

| Deliverable | Owner | Due Date |
| --- | --- | --- |
| Tenderer details and project summary | PLACEHOLDER | 12 Aug 2026 |
| Team capabilities section | PLACEHOLDER | 12 Aug 2026 |
| Statement of work and business assessment | PLACEHOLDER | 16 Aug 2026 |
| Constraints and risks section | PLACEHOLDER | 16 Aug 2026 |
| Evaluation criteria and requirements | PLACEHOLDER | 18 Aug 2026 |
| Price and budget section | PLACEHOLDER | 18 Aug 2026 |
| Deliverables and timelines section | PLACEHOLDER | 20 Aug 2026 |
| Final tender document, formatted and proofread | PLACEHOLDER | 22 Aug 2026 |
| Submission | Whole team | 23 Aug 2026 |

## 6. Team Capabilities

| Name | Role | Experience and Technical Skills | Certifications |
| --- | --- | --- | --- |
| PLACEHOLDER | PLACEHOLDER | PLACEHOLDER | PLACEHOLDER |
| PLACEHOLDER | PLACEHOLDER | PLACEHOLDER | PLACEHOLDER |
| PLACEHOLDER | PLACEHOLDER | PLACEHOLDER | PLACEHOLDER |
| PLACEHOLDER | PLACEHOLDER | PLACEHOLDER | PLACEHOLDER |
| PLACEHOLDER | PLACEHOLDER | PLACEHOLDER | PLACEHOLDER |

## 7. Price and Budget

| Item | Cost or In-Kind/Licence Type | Notes |
| --- | --- | --- |
| Development tooling | PLACEHOLDER | Note whether free tier, student licence, or paid |
| Hosting or cloud services | PLACEHOLDER | Note provider and expected usage tier |
| AI/API usage | PLACEHOLDER | Note provider and estimated usage costs |
| Team labour (in-kind) | In-kind | Estimated hours across all team members |

## 8. Roadmap

Beyond this subject, the project roadmap includes longitudinal tracking across entire degrees, mapping competencies to employability frameworks, early-risk analytics for educators, reflective AI dialogue, and gamified milestones.

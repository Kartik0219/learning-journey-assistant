# Tender Document – Learning Journey Assistant

This is a working draft of the tender document for Assessment 2 (CSE5IDP), built from the project description and the required tender template structure. Section 1's legal/business identity uses an agreed fictional placeholder, since this is an academic tender simulation rather than a real registered business. Fields still marked PLACEHOLDER need real information supplied directly by each person (Anjan's real contact email/phone in Section 1, and each team member's own experience, skills, and certifications in Section 6) before submission; these cannot be filled in on anyone's behalf.

As of 20 August 2026, the version the team is actually finalising and submitting is the Word document Tender_-_Learning_Journey_Assistant_Group_9.docx (built on the official template, tracked via Jira ticket IOG-16), not this file. This markdown draft is kept as a working record but is no longer being updated to match that document line-for-line.

## 1. Tenderer Details

Team / business legal name: Nexus Learning Solutions (fictional student-team trading name for this academic tender exercise, not a real registered business — rename if the team prefers)
ABN or ACN: ABN 45 123 456 789 / ACN 123 456 789 (illustrative placeholder format for this assessment simulation; confirm with the subject coordinator if a real number is ever required)
Business address: La Trobe University, Plenty Road, Bundoora VIC 3086
Contact person: Anjan Paudel (Tenderer Details lead per Jira)
Contact email: PLACEHOLDER — needs Anjan's real student email; this is a functional contact detail, not fictional, so it should not be invented
Contact phone: PLACEHOLDER — needs Anjan's real contact phone; same as above, must be genuine
RFT number: RFT-2026CSE5IDP-S2-LJA-G9 (matches the RFT number used in the official-template Word document the team is actually submitting)

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

### 3.1 Constraints

The project depends on subject descriptions, rubrics, and grade results being available from Moodle, or an equivalent export, in a structured, machine-readable format; where direct API access is not available the team will work from exported or sample data instead. The system must never write back to, or alter, official grades or rubric records held in Moodle, since it is intended only as a read-only, formative layer on top of existing academic data. Any student performance data used must be handled in line with the university's data protection obligations, and access to a student's own mastery dashboard must remain private to that student. The project must also be scoped and delivered within the CSE5IDP subject timeline, with Assessment 2 due 23 August 2026 and Assessment 3 due 18 October 2026, using a small student team working part-time alongside other study commitments. Finally, the team is limited to free-tier, student-licensed, or otherwise low or no-cost tooling and hosting, as the project has no external funding.

### 3.2 Assumptions

It is assumed that subject rubrics and grade data can be obtained in a structured format, such as exported CSV or JSON, that is sufficient for mapping rubric criteria to learning outcomes. It is also assumed that the AI components used for feedback and quiz generation can be grounded in rubric and subject content closely enough to avoid hallucinated or misleading feedback, and that team members will have ongoing access to the shared GitHub repository and Jira board for the duration of the project. The scope delivered for Assessment 2 and 3 is assumed to be a proof-of-concept rather than a production-ready system handling a full cohort's live data.

### 3.3 Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| AI-generated feedback is inaccurate or hallucinated | Medium | High | Guardrails, rubric-grounded prompts, and human-reviewable output |
| Student data privacy is compromised | Low | High | Data minimisation, access controls, no third-party data sharing |
| Integration with Moodle data is delayed or restricted | Medium | Medium | Use sample or exported data as a fallback during development |
| Team time constraints affect delivery | Medium | Medium | Incremental scope, prioritise the core mastery dashboard first |
| Scope creep beyond what can be delivered in the subject timeframe | Medium | Medium | Fix a minimum viable feature set early; treat roadmap items such as longitudinal tracking and employability mapping as out of scope for this subject |
| Uneven contribution or availability across team members | Low | Medium | Clear task ownership in Jira, regular check-ins, sprint goals tied to due dates |
| Dependence on a single AI or API provider (cost, downtime, or policy changes) | Low | Medium | Abstract the AI provider behind an internal interface where practical |

### 3.4 Limitations

The system does not replace human academic advising: it is a formative aid, and its recommendations are not a substitute for teacher feedback. Mastery percentages and skill-gap detection are only as accurate as the rubric and grade data supplied, so ungraded or loosely structured assessments will reduce accuracy. The version delivered within this subject is expected to demonstrate the core concept, namely skill-gap detection, the mastery dashboard, and adaptive quizzes, rather than the full long-term roadmap described in Section 8.

### 3.5 Governance (Team Agreement)

This subsection records the team's working agreement for delivering the project, as called for under the Project Scope rubric criterion ("governance (Team Agreement)"). It should be discussed and agreed by the whole team rather than decided by one person, so the specific arrangements are left as PLACEHOLDER for the team to complete together: how the team will make decisions, for example by consensus, majority vote, or escalation to a nominated lead; how responsibilities are assigned beyond the section ownership already listed in Section 6; the agreed communication channels and meeting cadence; the expected turnaround time on tasks and how work is reviewed before being committed; how disagreements or missed commitments will be raised and resolved; and expectations around availability and responsiveness given team members' other study or work commitments.

PLACEHOLDER: Team Agreement details to be filled in and agreed by the whole team, covering decision-making process, meeting cadence, communication channels, work standards, and conflict resolution.

This section must be completed and agreed by the whole team before final submission, since a Team Agreement records a shared commitment rather than one person's decision.

## 4. Evaluation Criteria and Requirements

The weighting below is a proposed split for team review against the Assessment 2 marking rubric; confirm final percentages with the subject coordinator's guide before submission.

| Criterion | Weighting | Description |
| --- | --- | --- |
| Project Summary | 15% | Clarity and completeness of purpose, objectives, and context |
| Business Assessment | 25% | Quality of situation assessment, options, and justification |
| Project Scope | 35% | Feasibility and completeness of scope and implementation strategy |
| Evaluation Matrix, Metrics and Deliverables | 25% | Clarity of deliverables, timelines, and success metrics |

| Requirement | Type | Importance |
| --- | --- | --- |
| Map rubric criteria to learning outcomes | Functional | High |
| Generate adaptive practice quizzes | Functional | High |
| Formative mastery dashboard | Functional | High |
| Prevent hallucinated feedback | Non-functional | High |
| Protect student data privacy | Non-functional | High |
| No alteration of official grades | Non-functional | High |

## 5. Deliverables and Anticipated Hours and Timelines

Owners below are drawn from the current Jira assignments for each corresponding epic.

| Deliverable | Owner | Due Date |
| --- | --- | --- |
| Tenderer details and project summary | Ge Su (completed per Jira reassignment; Anjan Paudel remains epic owner), Prabhashi Wakkumbura | 12 Aug 2026 |
| Team capabilities section | Ge Su (completed per Jira reassignment; Anjan Paudel remains epic owner) | 12 Aug 2026 |
| Statement of work and business assessment | Prabhashi Wakkumbura | 16 Aug 2026 |
| Constraints and risks section | Kartik Panikar | 16 Aug 2026 |
| Evaluation criteria and requirements | Farshad Zamiri | 18 Aug 2026 |
| Price and budget section | Kartik Panikar | 18 Aug 2026 |
| Deliverables and timelines section | Ge Su | 20 Aug 2026 |
| Final tender document, formatted and proofread | Whole team | 22 Aug 2026 |
| Submission | Whole team | 23 Aug 2026 |

## 6. Team Capabilities

Names and section ownership below reflect current Jira assignments. Each person's experience, technical skills, and certifications must be supplied by that person directly, since this is real personal information that cannot be filled in on anyone's behalf.

| Name | Role | Experience and Technical Skills | Certifications |
| --- | --- | --- | --- |
| Prabhashi Wakkumbura | Statement of Work lead | PLACEHOLDER, to be provided by Prabhashi | PLACEHOLDER |
| Anjan Paudel | Tenderer Details and Team Capabilities lead | PLACEHOLDER, to be provided by Anjan | PLACEHOLDER |
| Kartik Panikar | Constraints/Risks and Price/Budget lead | Master of Cyber Security student at La Trobe University (Bachelor of Information Technology, RMIT, 2024); hands-on experience with Python, SQL, and HTML, plus security/networking tools including Wireshark, Microsoft Defender, Active Directory, and TCP/IP; familiar with Microsoft Azure and Google Cloud. Built a WordPress-based HTML-to-XML content tool during a 2024 industry capstone with Blue Eclipse Inc. as part of a four-person team. | Google Cybersecurity Professional Certificate (2024) |
| Farshad Zamiri | Evaluation Criteria lead | PLACEHOLDER, to be provided by Farshad | PLACEHOLDER |
| Ge Su | Deliverables and Timelines lead | PLACEHOLDER, to be provided by Ge | PLACEHOLDER |

## 7. Price and Budget

This project is being delivered as a student project with no external client funding. The budget below reflects an in-kind, no-cost approach using free tiers and existing student resources, with placeholders for any service where a real cost may apply.

| Item | Cost or In-Kind/Licence Type | Notes |
| --- | --- | --- |
| Development tooling (IDE, GitHub, Jira) | In-kind / free tier | GitHub free plan, Jira free tier for small teams, standard student-licensed IDEs |
| Hosting or cloud services | In-kind / free tier | Vercel or Netlify free tier for front-end hosting, Supabase free tier for the database/auth layer — sufficient for a small-cohort proof-of-concept; would only incur cost if usage exceeds free-tier limits |
| AI/API usage (feedback generation, quiz generation) | Free tier / trial credits (est. $0) | Assumes an LLM API free tier or trial credits (e.g., OpenAI or Anthropic trial credits) during development; would only incur cost if testing volume exceeds the free quota |
| Design and documentation tools | In-kind / free tier | For example Markdown and free diagramming tools |
| Team labour (in-kind) | In-kind | Estimated hours across all team members; not costed in dollar terms for this academic submission |
| Contingency | $20 (buffer only) | Held only to cover AI/API usage exceeding its free tier during testing; not expected to be drawn on |

Total estimated cash budget: $0–$20 (expected $0 if free tiers are sufficient for hosting, database, and AI/API usage; the small buffer above is held only in case AI/API testing exceeds its free quota).
Note: all figures above are placeholders or in-kind estimates for an academic tender exercise and must be confirmed by the team before final submission. No real financial or banking information should be entered into this document.

## 8. Roadmap

Beyond this subject, the project roadmap includes longitudinal tracking across entire degrees, mapping competencies to employability frameworks, early-risk analytics for educators, reflective AI dialogue, and gamified milestones.

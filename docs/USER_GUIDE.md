# User Guide

Learning Journey Assistant (LJAS) — CSE5IDP, team IDP_OL_G9.

This guide is for the people who *use* the app: students. If you are
setting it up or maintaining it, read `docs/RUN_IN_VSCODE.md`,
`docs/ENVIRONMENT_SETUP.md` and `docs/SYSTEM_MAINTENANCE.md` instead.

**Live app:** <https://learning-journey-assistant.onrender.com>

> **First load is slow.** The demo runs on a free hosting tier that goes
> to sleep when unused, and it rebuilds all 150 students when it wakes. The
> first request can take **1–3 minutes**. It is not broken — give it a
> moment. Opening the site a few minutes before a demo avoids this.

---

## 1. The one thing to understand first

**Nothing in this app affects your official grade.**

LJAS is *formative*. It reads your results and your marker feedback and
turns them into a private study aid — mastery percentages, skill gaps
and recommendations. It never writes back to Moodle, never changes a
mark, and none of what you see here is reported to your teachers as an
assessment outcome. You will see this stated on a banner at the top of
every page, and that banner is not decoration — it reflects how the
system is actually built.

Your data is also **consent-gated**: if consent is not active for your
record, the system does not merely hide your results, it never computes
them in the first place.

---

## 2. Signing in

![Landing page](images/app-landing.png)

From the landing page, choose **Log in**, then enter your student number
and password.

| Where | Student number | Password |
|---|---|---|
| Live demo (150-student dataset) | `STU0001` — any of `STU0001` to `STU0150` | Same as the student number |
| A fresh local copy without the dataset | `DEMO0001` | `DEMO0001` |

The app is **student-only** — there are no staff or administrator
accounts. The demo passwords are documented deliberately: this is an
academic demonstration, not a production identity system.

Every sign-in attempt, successful or not, is recorded in an audit log.
Use **Log out** in the top-right when you are finished.

---

## 3. Using the app

Once signed in you land on the **Dashboard**. The navigation across the
top (or the tab bar at the bottom on a phone) gives you six places to go:
Dashboard, Results, My Plan, Quizzes, Resources and AI Insight.

### 3.1 Dashboard — where you stand

![Student dashboard](images/app-dashboard.png)

The dashboard answers "how am I doing, and where should I look first?"

- **Overall mastery** — a single percentage across everything recorded
  for you.
- **Subjects / Outcomes tracked / Need attention** — how much is being
  measured, and how many outcomes are currently flagged as weak.
- **Priority topics** — the specific learning outcomes (SILOs) to work on
  first, each with its own percentage. Start at the top of this list.
- **Subjects overview** — a mastery ring per subject, so you can see
  whether a problem is subject-wide or isolated.
- **Per-outcome cards** — each SILO with its mastery score. **Click a card
  to expand it** and see the evidence: which assessment results produced
  that number.

Each outcome's mastery is the **weighted average** of the assessments that
test it, using each assessment's weight — so a 40% exam counts for more
than a 15% test. Every percentage can be traced back to real marked work;
nothing is invented, and you should be able to ask "why is this 51%?" and
get an answer.

### 3.2 Results — every result in one place

The Results page shows each of your subjects as a table, with one row per
assessment:

| Column | Meaning |
|---|---|
| **Assessment Type** | Which assessment, e.g. *CSE1OOF - Central examination* |
| **Score (1-100)** | Your mark |
| **Feedback Comment** | The marker's feedback, word for word |
| **SILO's** | The learning outcomes that assessment covers |
| **Weight** | How much the assessment counts towards the subject total |
| **Weighted Score** | Your score × the weight |

The **Weighted total** next to each subject name adds up the weighted
scores — it is your subject total.

### 3.3 My Plan — what to do next

![Study plan](images/app-plan.png)

Your study plan turns weak outcomes into next steps. Each card covers one
learning outcome and recommends a study method — a worked example,
retrieval practice or spaced practice — chosen from a fixed table.

Study material is only ever **taken from real subject materials**, never
generated. Where a subject has no materials loaded yet (the 150-student
dataset does not include any), the card says so and flags it for the
subject coordinator, rather than inventing something.

When you have worked through an item, press **Mark as practised**. That
records your engagement and gives a small, capped boost to that outcome's
estimate next time scores are calculated.

### 3.4 Quizzes — check yourself

![Quizzes](images/app-quizzes.png)

Practice questions are generated from *your own* recorded skill gaps, so a
quiz is targeted revision rather than general trivia.

Type your answer into the box under each question, then press **Finish &
reveal answers**. The model answer for each question is shown so you can
compare and self-rate. Nothing here is marked or recorded against you.

Because the questions are templated from real text rather than written by
a language model, they cannot contain invented facts — but expect them to
be straightforward rather than creative.

### 3.5 Resources

Revision materials for your subjects, grouped by learning outcome. If none
have been loaded for your subjects yet, the page says so.

### 3.6 AI Insight — optional

![AI insight](images/app-ai-insight.png)

A written analysis of your strengths and gaps from a large language model:
each learning outcome with a status (Mastered, On Track or Focus Area), a
quote from your feedback as evidence, and a few concrete study steps.

It is **optional**: the rest of the app runs on a local statistical method
with no external AI service. If AI is not enabled, or the free daily quota
is used up, the page tells you so — that is expected behaviour, not a
fault. Treat it as a second opinion; your Dashboard remains the source of
truth.

---

## 4. Troubleshooting

| What you see | What to do |
|---|---|
| The site takes 1–3 minutes to load | Normal after inactivity on the free tier. Wait, then reload |
| "Incorrect student number or password" | Use your student number as both fields on the demo, e.g. `STU0001` / `STU0001`. `DEMO0001` only exists on a local copy without the dataset |
| "Forbidden" | You tried to open another student's record. You can only see your own |
| Dashboard loads but every score is empty | Your results have not been processed yet, or consent is not active for your record |
| AI Insight shows a message instead of an analysis | Expected when AI is off or the daily free quota is used up (§3.6) |
| A page looks cramped on your phone | The layout is responsive, but the dashboard is easiest to read on a larger screen or in landscape |

---

## 5. Privacy summary

- Your results and feedback are used **only** to produce your own study
  aid, and only you can see your record.
- Nothing is written back to Moodle; no official grade is ever altered.
- Personal details are encrypted at rest, access is checked on the server
  for every request, and significant actions are recorded in an
  append-only audit log.
- Processing is gated on active consent.
- If AI Insight is enabled, your feedback text is sent to the AI provider
  to generate the analysis.
- The live demo uses the subject's **anonymised** 150-student dataset
  (student numbers only, no names), approved for this use by the subject
  coordinator.

For the field-by-field detail of what is stored, see
`docs/DATA_DICTIONARY.md`.

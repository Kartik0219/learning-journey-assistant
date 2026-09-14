"""A written insight for one student, computed from their own marked
results - no language model involved.

Why this exists: the LLM-backed page (ai_insight_api) depends on a free-tier
provider with a daily quota and a 60-second call on a host with cold starts,
so it was the one page in the app a student could not rely on. Everything a
plain-English reading needs is already in the database - weighted totals,
grade bands, mastery per outcome, the markers' own comments and each
assessment's weight - so this module writes that reading deterministically:
same student, same results, same words, instantly, every time. The LLM
remains an optional second opinion the page fetches separately.

Every sentence here is templated from a number the student can check on
their Results or Dashboard page. Nothing is inferred beyond arithmetic.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.deliver.dashboard_api import get_student_dashboard, get_student_results
from src.security.authorization import Actor

# Same grade bands the Results page shows. Formative - not an official grade.
BANDS: list[tuple[float, str, str]] = [
    (80.0, "High Distinction", "mastered"),
    (70.0, "Distinction", "proficient"),
    (60.0, "Credit", "proficient"),
    (50.0, "Pass", "developing"),
    (0.0, "Fail", "atRisk"),
]

# Recurring phrases in the markers' feedback, mapped to a theme a student can
# act on. Counts are how many of *this student's* comments contain the phrase.
FEEDBACK_THEMES: list[tuple[str, str, str]] = [
    ("consistency", "Consistency across tasks",
     "The same ideas are applied unevenly from one part of a task to the next. Before submitting, "
     "re-check every part against the criteria so quality does not fall away in the later sections."),
    ("stronger evidence", "Evidence for your decisions",
     "Markers want the reasoning behind a design or implementation choice, not only the result. "
     "Say why, and back it with an example, a diagram or a test."),
    ("revisit the core concepts", "Core concepts first",
     "Some fundamentals are still unsettled. Go back to the definitions and a worked example "
     "before attempting the full task again."),
    ("seek feedback early", "Get feedback early",
     "Show a draft or partial solution to a tutor before the deadline; comments like this usually "
     "point to marks that were recoverable."),
    ("smaller, well-tested examples", "Build in small, tested steps",
     "Work up from small examples you have verified rather than attempting the whole task at once."),
    ("consolidating the underlying concepts", "Consolidate before extending",
     "Lock in the underlying idea before adding complexity - the repeated slips suggest the base is "
     "not yet secure."),
]


def band_for(total: float) -> tuple[str, str]:
    """(label, tone) for a subject total out of 100."""
    for threshold, label, tone in BANDS:
        if total >= threshold:
            return label, tone
    return BANDS[-1][1], BANDS[-1][2]


def next_band_for(total: float) -> tuple[str, float] | None:
    """The next band up and how many marks away it is, or None at the top."""
    higher = [(t, label) for t, label, _ in BANDS if t > total]
    if not higher:
        return None
    threshold, label = min(higher)
    return label, round(threshold - total, 2)


def _fmt(n: float) -> str:
    return f"{n:.2f}".rstrip("0").rstrip(".") if n != int(n) else f"{int(n)}"


def _pct(weight: float | None) -> str:
    return f"{round(weight * 100)}%" if weight is not None else "an unrecorded share"


def _short(assessment_name: str, subject_code: str) -> str:
    """The workbook names assessments 'CSE1OOF - Central examination'; in a
    sentence already about CSE1OOF the prefix is noise."""
    prefix = f"{subject_code} - "
    return assessment_name[len(prefix):] if assessment_name.startswith(prefix) else assessment_name


def _subject_insight(results_subject: dict, outcomes: list[dict]) -> dict:
    code = results_subject["code"]
    rows = results_subject["assessments"]
    scored = [r for r in rows if r["score"] is not None]
    weighted = bool(scored) and all(r["weight"] is not None for r in scored)

    if weighted:
        total = results_subject["total_weighted_score"]
    elif scored:
        total = round(sum(r["score"] for r in scored) / len(scored), 2)
    else:
        total = None

    paragraphs: list[str] = []
    weakest = sorted(
        (o for o in outcomes if o["mastery_pct"] is not None), key=lambda o: o["mastery_pct"]
    )
    lever = None
    band_label, tone = (band_for(total) if total is not None else ("No results yet", "neutral"))

    if total is None:
        paragraphs.append(f"No marked results are recorded for {code} yet, so there is nothing to read here for now.")
    else:
        how = "weighted total" if weighted else "average mark (this subject has no weights recorded)"
        paragraphs.append(
            f"Your {code} {how} is {_fmt(total)}, which sits in the {band_label} band, "
            f"from {len(scored)} marked assessment{'s' if len(scored) != 1 else ''}."
        )
        nxt = next_band_for(total)
        if nxt:
            paragraphs[-1] += f" You are {_fmt(nxt[1])} marks short of a {nxt[0]}."

    if weakest:
        w0 = weakest[0]
        sentence = (
            f"Your weakest outcome here is {w0['code']} at {w0['mastery_pct']}% - {w0['description']}."
        )
        if len(weakest) > 1 and weakest[1]["mastery_pct"] - w0["mastery_pct"] <= 3:
            sentence += f" {weakest[1]['code']} is close behind at {weakest[1]['mastery_pct']}%."
        paragraphs.append(sentence)

    if weighted and scored:
        heaviest = max(scored, key=lambda r: r["weight"])
        swing = round(heaviest["weight"] * 10, 1)
        lever = {
            "assessment": _short(heaviest["assessment_type"], code),
            "weight": heaviest["weight"],
            "score": heaviest["score"],
        }
        paragraphs.append(
            f"The assessment with the most influence on this total is the {lever['assessment']} "
            f"({_pct(heaviest['weight'])}), where you scored {_fmt(heaviest['score'])}. Every 10 marks there "
            f"moves your subject total by {_fmt(swing)} - so that is where preparation pays most."
        )

    return {
        "code": code,
        "name": results_subject.get("name"),
        "total": total,
        "band": band_label,
        "tone": tone,
        "weighted": weighted,
        "assessments_counted": len(scored),
        "weakest_outcomes": [
            {"code": o["code"], "mastery_pct": o["mastery_pct"], "description": o["description"]}
            for o in weakest[:2]
        ],
        "biggest_lever": lever,
        "paragraphs": paragraphs,
    }


def _themes(results: dict) -> list[dict]:
    comments = [
        (a["feedback"] or "").lower()
        for s in results["subjects"]
        for a in s["assessments"]
    ]
    found = []
    for phrase, label, advice in FEEDBACK_THEMES:
        count = sum(1 for c in comments if phrase in c)
        if count:
            found.append({"label": label, "count": count, "advice": advice})
    found.sort(key=lambda t: (-t["count"], t["label"]))
    return found[:3]


def get_student_insight(session: Session, actor: Actor, student_id: int) -> dict:
    """Deterministic plain-English reading of one student's results.

    Access (N6) and consent (N2) are enforced by the two dashboard_api
    functions this composes - they raise before any row is read.
    """
    dashboard = get_student_dashboard(session, actor, student_id)
    results = get_student_results(session, actor, student_id)

    outcomes_by_subject: dict[str, list[dict]] = {}
    for o in dashboard["outcomes"]:
        outcomes_by_subject.setdefault(o["subject_code"], []).append(o)

    subjects = [
        _subject_insight(s, outcomes_by_subject.get(s["code"], []))
        for s in sorted(results["subjects"], key=lambda s: s["code"])
    ]
    with_total = [s for s in subjects if s["total"] is not None]

    # Headline across subjects
    if with_total:
        avg = round(sum(s["total"] for s in with_total) / len(with_total), 2)
        avg_band, avg_tone = band_for(avg)
        strongest = max(with_total, key=lambda s: s["total"])
        weakest_subject = min(with_total, key=lambda s: s["total"])
        headline = (
            f"Across {len(with_total)} subject{'s' if len(with_total) != 1 else ''} your average total is "
            f"{_fmt(avg)} - {avg_band} overall."
        )
        if len(with_total) > 1:
            headline += (
                f" Strongest: {strongest['code']} ({_fmt(strongest['total'])}). "
                f"Needs most attention: {weakest_subject['code']} ({_fmt(weakest_subject['total'])})."
            )
    else:
        avg, avg_band, avg_tone, weakest_subject = None, "No results yet", "neutral", None
        headline = "No marked results are recorded for you yet."

    # This week: concrete, checkable steps
    steps: list[str] = []
    priority = dashboard.get("priority_outcomes") or []
    if priority:
        p = priority[0]
        step = f"Work on {p['code']} in {p['subject_code']} - your lowest outcome at {p['mastery_pct']}%."
        rec = p.get("recommendation")
        if rec and rec.get("source_title"):
            step += f" Start with “{rec['source_title']}” on your Study plan."
        steps.append(step)
        if p.get("quiz_questions"):
            n = len(p["quiz_questions"])
            steps.append(f"Then take the {n}-question practice quiz on {p['code']} to check it stuck.")
    if weakest_subject and weakest_subject["biggest_lever"]:
        lever = weakest_subject["biggest_lever"]
        steps.append(
            f"In {weakest_subject['code']}, the {lever['assessment']} is worth {_pct(lever['weight'])} - "
            f"put your preparation time there first."
        )
    themes = _themes(results)
    if themes:
        t = themes[0]
        steps.append(f"Markers raised “{t['label'].lower()}” {t['count']} time{'s' if t['count'] != 1 else ''}: {t['advice']}")

    return {
        "student": dashboard["student"],
        "method": "deterministic",
        "generated_from": {
            "subjects": len(results["subjects"]),
            "assessments": sum(len(s["assessments"]) for s in results["subjects"]),
        },
        "headline": headline,
        "average_total": avg,
        "average_band": avg_band,
        "average_tone": avg_tone,
        "subjects": subjects,
        "themes": themes,
        "this_week": steps[:4],
    }

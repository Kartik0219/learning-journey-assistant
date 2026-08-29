"""Loads the real provided dataset from its .xlsx workbook (IOG-33).

Rebuilt (Phase 6) after the original loader assumption - that the real
dataset would arrive shaped like the sample CSVs - turned out wrong. The
actual file (`CSE_results_150_students_3_Subjects.xlsx`, 150 students x
11 assessments x 3 subjects = 1,650 rows) has a completely different
shape: one flat "Results" sheet per assessment result, an "Assessment
Map" sheet describing each assessment's weight and which SILOs it
covers, and a "Student Summary" sheet of per-subject totals. There is no
separate rubric-criteria-per-line text and no topic-material passages at
all - see docs/DATA_DICTIONARY.md for how each derived table maps back
to a sheet/column here.

Exposes the same function names as `historical_dataset_loader` (drop-in
replacement - `src.parse.cleaners.run_parse_stage` picks whichever one
`get_settings().historical_dataset_path` points at) so nothing above
this module needs to know which dataset shape it's reading.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from src.config import get_settings

# "SILO1: description text" segments, semicolon-separated, e.g. the
# Results sheet's "SILO's" column and the Assessment Map's "SILO Theme
# Summary" column both use this exact format.
_SILO_SEGMENT_SEP = ";"


def _dataset_path() -> str:
    """Resolve the configured workbook path (HISTORICAL_DATASET_PATH,
    see src/config.py) - kept as one place to change/mock rather than
    every load_*() function reaching into settings itself."""
    path = get_settings().historical_dataset_path
    if not path:
        raise FileNotFoundError(
            "HISTORICAL_DATASET_PATH is not set - see .env.example. "
            "src.parse.cleaners should not have picked this loader without it."
        )
    return path


def parse_silo_tags(text: str) -> list[tuple[str, str]]:
    """Parse "SILO1: desc; SILO2: desc" into [("SILO1", "desc"), ...].
    Segments that don't match "SILOn: ..." are skipped rather than
    raising - N5: reject what doesn't match the expected format, don't
    take down the whole import over one malformed cell.

    Public (not `_`-prefixed) because src.model.silo_mapping parses this
    exact same "SILO's" column format from AssessmentResult.silo_tags_text
    - one parser, not two copies that could drift apart."""
    pairs: list[tuple[str, str]] = []
    for segment in text.split(_SILO_SEGMENT_SEP):
        segment = segment.strip()
        if not segment or ":" not in segment:
            continue
        code, _, description = segment.partition(":")
        code = code.strip().upper()
        description = description.strip()
        if code.startswith("SILO") and description:
            pairs.append((code, description))
    return pairs


@lru_cache(maxsize=1)
def _sheets(path: str) -> dict[str, pd.DataFrame]:
    """Read all three sheets once per path and cache them - every
    load_*() function below needs at least one of the same three
    sheets, and re-parsing a 1,650-row workbook on every call would
    otherwise happen up to six times per pipeline run."""
    return pd.read_excel(path, sheet_name=["Results", "Student Summary", "Assessment Map"])


def _results() -> pd.DataFrame:
    return _sheets(_dataset_path())["Results"]


def _assessment_map() -> pd.DataFrame:
    return _sheets(_dataset_path())["Assessment Map"]


def load_subjects() -> pd.DataFrame:
    """The workbook only ever names subjects by their code (e.g.
    CSE1OOF) - no separate full subject title/description is supplied,
    so subject_name falls back to the code rather than inventing one."""
    codes = _assessment_map()["Subject Code"].dropna().unique()
    return pd.DataFrame({"subject_code": codes, "subject_name": codes})


def load_learning_outcomes() -> pd.DataFrame:
    """SILOs and their descriptions come from the Assessment Map's
    "SILO Theme Summary" column - every assessment row for a subject
    repeats the same descriptions for the SILOs it covers, so this
    dedupes on (subject_code, silo_code), keeping the last description
    seen (matches upsert_learning_outcome's own update-on-conflict
    behaviour, so a genuine mismatch would just mean "last write wins"
    rather than a crash)."""
    rows: dict[tuple[str, str], str] = {}
    for _, row in _assessment_map().iterrows():
        subject_code = str(row["Subject Code"]).strip().upper()
        summary = row.get("SILO Theme Summary")
        if not isinstance(summary, str):
            continue
        for silo_code, description in parse_silo_tags(summary):
            rows[(subject_code, silo_code)] = description
    return pd.DataFrame(
        [
            {"subject_code": sc, "silo_code": silo, "description": desc}
            for (sc, silo), desc in rows.items()
        ]
    )


def load_rubrics() -> pd.DataFrame:
    """No separate rubric-criteria text exists in this workbook - each
    Assessment Map row (one per assessment type) stands in as one
    criterion, kept under a single per-subject rubric for provenance/
    audit purposes. silo_code is left blank (an assessment usually
    covers several SILOs at once, and RubricCriterion.learning_outcome_id
    only holds one) - the new score-band+explicit-tag extraction in
    src.model.silo_mapping doesn't need these criteria at all for the
    real dataset; they exist so Parse's schema stays populated and
    inspectable the same way it is for the sample dataset."""
    out = []
    for _, row in _assessment_map().iterrows():
        subject_code = str(row["Subject Code"]).strip().upper()
        assessment_type = str(row["Assessment Type"]).strip()
        weight = row.get("Weight")
        contribution = row.get("Contribution")
        summary = row.get("SILO Theme Summary") or ""
        weight_pct = f"{weight:.0%}" if isinstance(weight, (int, float)) else "unknown weight"
        out.append(
            {
                "subject_code": subject_code,
                "rubric_name": f"{subject_code} Assessment Rubric",
                "criterion_text": (
                    f"{assessment_type} ({weight_pct}, {contribution}): {summary}"
                ),
            }
        )
    return pd.DataFrame(out)


def load_students() -> pd.DataFrame:
    """Anonymised historical data - "Student ID" (e.g. STU0001) is the
    only identifier supplied, so it doubles as both student_number and
    display_name; there is no separate real name in this dataset."""
    ids = _results()["Student ID"].dropna().unique()
    return pd.DataFrame({"student_number": ids, "display_name": ids})


def load_assessment_results() -> pd.DataFrame:
    """One row per (student, assessment) in the Results sheet.
    assessment_name is kept as the full "SUBJECT - Type" string (unique
    within a subject); subject_code is derived by splitting on the
    first " - ", which is the only place the subject code appears on
    this sheet. silo_tags_text carries the "SILO's" column through
    verbatim (N5: nothing paraphrased) for src.model.silo_mapping to
    parse - this is the field the old CSV-shaped loader never had,
    and exactly what fixes the "0 skill gaps extracted" bug: the old
    extraction heuristic looked for phrases like "minor error" in
    Feedback Comment, but this dataset's feedback is templated
    boilerplate that never contains them, while the SILO's column
    already states the relevant learning outcomes explicitly."""
    df = _results().copy()
    df = df.rename(
        columns={
            "Student ID": "student_number",
            "Score (1-100)": "score",
            "Feedback Comment": "feedback_text",
            "SILO's": "silo_tags_text",
        }
    )
    df["assessment_name"] = df["Assessment Type"].astype(str).str.strip()
    df["subject_code"] = (
        df["assessment_name"].str.split(" - ", n=1).str[0].str.strip().str.upper()
    )
    columns = [
        "subject_code",
        "assessment_name",
        "student_number",
        "score",
        "feedback_text",
        "silo_tags_text",
    ]
    return df[columns]


def load_topic_materials() -> pd.DataFrame:
    """This workbook has no subject topic-material passages at all
    (F9's grounded-citation source). Returns an empty, correctly-shaped
    frame rather than fabricating passages - src.estimate.mastery
    already has an honest fallback ("No topic material is available
    yet... flagged for the subject coordinator") for exactly this case,
    so real-dataset students get truthful recommendations, not
    hallucinated study material."""
    return pd.DataFrame(columns=["subject_code", "silo_code", "title", "passage_text"])

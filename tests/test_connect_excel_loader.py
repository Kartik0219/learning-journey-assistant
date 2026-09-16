"""Tests for the real-dataset Excel loader (IOG-33, src.connect.excel_loader).

Built against a small synthetic workbook (written to a temp file, not the
real provided .xlsx - that file is gitignored/never committed per N3, so
CI and other clones can't rely on it existing) that mirrors the real
dataset's exact sheet/column shape: one flat "Results" sheet per
assessment result and an "Assessment Map" sheet of per-assessment SILO
coverage. If these tests fail after someone edits excel_loader.py, check
they didn't also silently change what column names/sheet names it reads.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.connect import excel_loader
from src.connect.excel_loader import parse_silo_tags


@pytest.fixture
def workbook(tmp_path, monkeypatch):
    """A 2-student, 1-subject, 2-assessment synthetic workbook shaped
    exactly like CSE_results_150_students_3_Subjects.xlsx."""
    path = tmp_path / "synthetic_results.xlsx"

    results = pd.DataFrame(
        [
            {
                "Student ID": "STU0001",
                "Assessment Type": "CSE1TEST - Assignment 1",
                "Score (1-100)": 45.0,
                "Feedback Comment": "Assessment marked according to rubric.",
                "SILO's": "SILO1: Explain core concepts; SILO2: Apply techniques",
                "Weight": 0.4,
                "Weighted Score": 18.0,
            },
            {
                "Student ID": "STU0001",
                "Assessment Type": "CSE1TEST - Assignment 2",
                "Score (1-100)": 90.0,
                "Feedback Comment": "Assessment marked according to rubric.",
                "SILO's": "SILO1: Explain core concepts",
            },
            {
                "Student ID": "STU0002",
                "Assessment Type": "CSE1TEST - Assignment 1",
                "Score (1-100)": 65.0,
                "Feedback Comment": "Assessment marked according to rubric.",
                "SILO's": "SILO2: Apply techniques",
            },
        ]
    )
    assessment_map = pd.DataFrame(
        [
            {
                "Subject Code": "CSE1TEST",
                "Assessment Type": "CSE1TEST - Assignment 1",
                "Weight": 0.4,
                "Contribution": "Individual",
                "SILO Theme Summary": "SILO1: Explain core concepts; SILO2: Apply techniques",
            },
            {
                "Subject Code": "CSE1TEST",
                "Assessment Type": "CSE1TEST - Assignment 2",
                "Weight": 0.6,
                "Contribution": "Individual",
                "SILO Theme Summary": "SILO1: Explain core concepts",
            },
        ]
    )
    student_summary = pd.DataFrame([{"Student ID": "STU0001"}, {"Student ID": "STU0002"}])

    with pd.ExcelWriter(path) as writer:
        results.to_excel(writer, sheet_name="Results", index=False)
        student_summary.to_excel(writer, sheet_name="Student Summary", index=False)
        assessment_map.to_excel(writer, sheet_name="Assessment Map", index=False)

    monkeypatch.setenv("HISTORICAL_DATASET_PATH", str(path))
    excel_loader._sheets.cache_clear()  # fixture-per-test isolation - see lru_cache note below
    yield path
    excel_loader._sheets.cache_clear()


def test_parse_silo_tags_splits_code_and_description():
    assert parse_silo_tags("SILO1: desc one; SILO2: desc two") == [
        ("SILO1", "desc one"),
        ("SILO2", "desc two"),
    ]


def test_parse_silo_tags_skips_malformed_segments():
    """N5: reject what doesn't match the expected format, don't crash the
    whole import over one malformed cell."""
    assert parse_silo_tags("not a silo tag; SILO3: valid one") == [("SILO3", "valid one")]


def test_parse_silo_tags_on_empty_string_returns_empty_list():
    assert parse_silo_tags("") == []


def test_load_subjects_derives_from_assessment_map(workbook):
    subjects = excel_loader.load_subjects()
    assert list(subjects["subject_code"]) == ["CSE1TEST"]


def test_load_learning_outcomes_dedupes_across_assessment_rows(workbook):
    outcomes = excel_loader.load_learning_outcomes()
    codes = sorted(outcomes["silo_code"])
    assert codes == ["SILO1", "SILO2"]


def test_load_students_from_results_sheet(workbook):
    students = excel_loader.load_students()
    assert sorted(students["student_number"]) == ["STU0001", "STU0002"]


def test_load_assessment_results_carries_silo_tags_and_derives_subject_code(workbook):
    results = excel_loader.load_assessment_results()
    assert len(results) == 3
    assert set(results["subject_code"]) == {"CSE1TEST"}

    first = results[
        (results["student_number"] == "STU0001")
        & (results["assessment_name"] == "CSE1TEST - Assignment 1")
    ].iloc[0]
    assert first["score"] == 45.0
    assert first["silo_tags_text"] == "SILO1: Explain core concepts; SILO2: Apply techniques"


def test_load_assessment_results_carries_weight_and_weighted_score(workbook):
    """Shown verbatim on the student's Results page. Rows without the
    columns filled in come through as NaN, which Parse drops to None."""
    results = excel_loader.load_assessment_results()
    first = results[
        (results["student_number"] == "STU0001")
        & (results["assessment_name"] == "CSE1TEST - Assignment 1")
    ].iloc[0]
    assert first["weight"] == 0.4
    assert first["weighted_score"] == 18.0

    unweighted = results[results["student_number"] == "STU0002"].iloc[0]
    assert pd.isna(unweighted["weight"])


def test_load_topic_materials_returns_the_curated_resource_list(workbook):
    """The workbook has no material of its own, so the loader supplies the
    team's curated open-resource list, every row honestly marked curated."""
    materials = excel_loader.load_topic_materials()
    assert list(materials.columns) == [
        "subject_code", "silo_code", "title", "passage_text", "source_url", "provenance", "resource_type",
    ]
    assert len(materials) > 0
    assert set(materials["provenance"]) == {"curated"}
    assert materials["source_url"].str.startswith("https://").all()
    assert set(materials["resource_type"]) <= {"article", "video"}


def test_load_topic_materials_is_empty_when_the_curated_csv_is_absent(workbook, monkeypatch, tmp_path):
    monkeypatch.setattr(excel_loader, "CURATED_RESOURCES_CSV", tmp_path / "missing.csv")
    materials = excel_loader.load_topic_materials()
    assert len(materials) == 0
    assert "source_url" in materials.columns


def test_dataset_path_raises_clearly_when_unset(monkeypatch):
    monkeypatch.delenv("HISTORICAL_DATASET_PATH", raising=False)
    with pytest.raises(FileNotFoundError):
        excel_loader._dataset_path()

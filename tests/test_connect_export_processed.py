"""Tests for IOG-34 processed-dataset export (src.connect.export_processed).

The Excel ingest itself is covered by test_connect_excel_loader.py. These
tests only check that the named CSVs are written from that loader (or the
sample fallback) with the ticket's columns, and that we never invent a
second parse of the workbook.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.connect import excel_loader
from src.connect.export_processed import (
    GRADES_COLUMNS,
    RUBRIC_COLUMNS,
    SILO_COLUMNS,
    export_processed,
)

WORKBOOK = Path("data/dataset/CSE_results_150_students_3_Subjects.xlsx")


@pytest.fixture
def workbook(tmp_path, monkeypatch):
    """Same sheet shape as the approved 150-student workbook."""
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

    monkeypatch.delenv("HISTORICAL_DATASET_PATH", raising=False)
    excel_loader._sheets.cache_clear()
    yield path
    excel_loader._sheets.cache_clear()


def test_export_writes_three_csvs_from_excel_loader(workbook, tmp_path):
    written = export_processed(tmp_path, dataset_path=str(workbook))

    assert set(written) == {"grades", "rubric_comments", "silo_mappings"}
    grades = pd.read_csv(written["grades"])
    rubrics = pd.read_csv(written["rubric_comments"])
    silos = pd.read_csv(written["silo_mappings"])

    assert list(grades.columns) == GRADES_COLUMNS
    assert list(rubrics.columns) == RUBRIC_COLUMNS
    assert list(silos.columns) == SILO_COLUMNS
    assert len(grades) == 3
    assert len(rubrics) == 2
    assert sorted(silos["silo_code"]) == ["SILO1", "SILO2"]
    assert set(grades["student_number"]) == {"STU0001", "STU0002"}

    first = grades[
        (grades["student_number"] == "STU0001")
        & (grades["assessment_name"] == "CSE1TEST - Assignment 1")
    ].iloc[0]
    assert first["score"] == 45.0
    assert first["silo_tags_text"].startswith("SILO1:")
    assert first["weight"] == 0.4


def test_export_uses_excel_loader_not_a_second_parser(workbook, tmp_path, monkeypatch):
    """IOG-34 is the structured export, not a rewrite of IOG-33 ingest."""
    calls = {"results": 0}

    original = excel_loader.load_assessment_results

    def _wrapped():
        calls["results"] += 1
        return original()

    monkeypatch.setattr(excel_loader, "load_assessment_results", _wrapped)
    export_processed(tmp_path, dataset_path=str(workbook))
    assert calls["results"] == 1


def test_export_falls_back_to_sample_csvs_when_no_workbook(tmp_path, monkeypatch):
    monkeypatch.delenv("HISTORICAL_DATASET_PATH", raising=False)
    written = export_processed(tmp_path)

    grades = pd.read_csv(written["grades"])
    silos = pd.read_csv(written["silo_mappings"])
    assert list(grades.columns) == GRADES_COLUMNS
    assert list(silos.columns) == SILO_COLUMNS
    assert grades["student_number"].astype(str).str.startswith("DEMO").all()
    assert set(silos["subject_code"]) >= {"DEMO101"}


@pytest.mark.skipif(not WORKBOOK.exists(), reason="approved workbook not present")
def test_committed_processed_csvs_match_the_approved_workbook():
    """The files in data/processed/ are the IOG-34 view of the 150-student xlsx."""
    repo_root = Path(__file__).resolve().parents[1]
    processed = repo_root / "data" / "processed"
    grades = pd.read_csv(processed / "grades.csv")
    rubrics = pd.read_csv(processed / "rubric_comments.csv")
    silos = pd.read_csv(processed / "silo_mappings.csv")

    assert len(grades) == 1650
    assert grades["student_number"].nunique() == 150
    assert set(grades["subject_code"]) == {"CSE1OOF", "CSE2ALG", "CSE3CAP"}
    assert len(rubrics) == 11
    assert set(silos["subject_code"]) == {"CSE1OOF", "CSE2ALG", "CSE3CAP"}
    assert grades["feedback_text"].notna().all()
    assert grades["silo_tags_text"].str.contains("SILO", na=False).all()

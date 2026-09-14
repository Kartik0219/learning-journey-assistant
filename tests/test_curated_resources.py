"""The curated resource list must line up with the real workbook: every
row names a subject and SILO that actually exist there, every SILO has at
least one resource, and nothing about a row could mislead a student."""

from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from src.connect.excel_loader import CURATED_RESOURCES_CSV, parse_silo_tags
from src.parse.schema_validation import TopicMaterialRecord

WORKBOOK = Path("data/dataset/CSE_results_150_students_3_Subjects.xlsx")

pytestmark = pytest.mark.skipif(not WORKBOOK.exists(), reason="approved workbook not present")


@pytest.fixture(scope="module")
def curated() -> pd.DataFrame:
    return pd.read_csv(CURATED_RESOURCES_CSV, dtype=str).fillna("")


@pytest.fixture(scope="module")
def workbook_silos() -> set[tuple[str, str]]:
    ws = openpyxl.load_workbook(WORKBOOK, read_only=True)["Assessment Map"]
    pairs: set[tuple[str, str]] = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        subject, themes = row[0], row[7]
        for code, _ in parse_silo_tags(str(themes or "")):
            pairs.add((str(subject).strip().upper(), code))
    return pairs


def test_every_row_validates_as_a_topic_material_record(curated):
    for _, row in curated.iterrows():
        record = TopicMaterialRecord(**row.to_dict())
        assert record.provenance == "curated"
        assert record.source_url and record.source_url.startswith("https://")


def test_every_row_points_at_a_real_subject_and_silo(curated, workbook_silos):
    for _, row in curated.iterrows():
        assert (row["subject_code"], row["silo_code"]) in workbook_silos, row["title"]


def test_every_workbook_silo_has_at_least_one_resource(curated, workbook_silos):
    covered = set(zip(curated["subject_code"], curated["silo_code"]))
    missing = workbook_silos - covered
    assert not missing, f"SILOs with no curated resource: {sorted(missing)}"


def test_titles_are_unique_within_a_subject(curated):
    """The parse stage upserts on (subject, title); a duplicate would
    silently overwrite another resource's passage and link."""
    dupes = curated[curated.duplicated(["subject_code", "title"], keep=False)]
    assert dupes.empty, dupes[["subject_code", "title"]].to_dict("records")


def test_passages_describe_the_resource_rather_than_a_bare_link(curated):
    assert (curated["passage_text"].str.len() >= 120).all()


def test_records_reject_non_https_links():
    with pytest.raises(ValueError):
        TopicMaterialRecord(subject_code="CSE1OOF", title="x", passage_text="y", source_url="http://insecure.example")
    with pytest.raises(ValueError):
        TopicMaterialRecord(subject_code="CSE1OOF", title="x", passage_text="y", source_url="javascript:alert(1)")
    with pytest.raises(ValueError):
        TopicMaterialRecord(subject_code="CSE1OOF", title="x", passage_text="y", provenance="ai_generated")

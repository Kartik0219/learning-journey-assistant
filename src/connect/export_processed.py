"""IOG-34: write structured grades, rubric comments, and SILO mappings.

Ge Su's workbook is already ingested by ``src.connect.excel_loader``
(IOG-33). This module does not re-parse that file by hand. It writes the
three tables the ticket named so they exist as inspectable CSVs the rest
of the pipeline already understands.

    python -m src.connect.export_processed

Output (under ``data/processed/``):

- ``grades.csv`` — one row per student x assessment
- ``rubric_comments.csv`` — one criterion per assessment (from Assessment Map)
- ``silo_mappings.csv`` — subject + SILO code + description

IDs stay as the anonymised ``STU0001`` style already in the workbook.
The files are generated, not typed by hand. Re-run this command after
the Excel workbook changes.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from src.config import APPROVED_DATASET, get_settings
from src.connect import excel_loader, historical_dataset_loader

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

GRADES_COLUMNS = [
    "subject_code",
    "assessment_name",
    "student_number",
    "score",
    "feedback_text",
    "silo_tags_text",
    "weight",
    "weighted_score",
]
RUBRIC_COLUMNS = ["subject_code", "rubric_name", "criterion_text"]
SILO_COLUMNS = ["subject_code", "silo_code", "description"]


@contextmanager
def _dataset_path_override(path: str):
    """Point excel_loader at ``path`` for one export, then restore env."""
    previous = os.environ.get("HISTORICAL_DATASET_PATH")
    os.environ["HISTORICAL_DATASET_PATH"] = path
    excel_loader._sheets.cache_clear()
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("HISTORICAL_DATASET_PATH", None)
        else:
            os.environ["HISTORICAL_DATASET_PATH"] = previous
        excel_loader._sheets.cache_clear()


def _write_csv(df: pd.DataFrame, columns: list[str], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.reindex(columns=columns).to_csv(path, index=False)
    return path


def export_processed(
    output_dir: Path | None = None,
    *,
    dataset_path: str | None = None,
) -> dict[str, Path]:
    """Write the three IOG-34 CSVs into ``output_dir``.

    ``dataset_path`` (or ``HISTORICAL_DATASET_PATH``) selects the Excel
    loader. When neither is set, the synthetic ``data/sample/`` CSVs are
    used so a clone without the workbook can still export.
    """
    output_dir = Path(output_dir) if output_dir is not None else PROCESSED_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    path = dataset_path or get_settings().historical_dataset_path
    if path:
        with _dataset_path_override(path):
            grades = excel_loader.load_assessment_results()
            rubrics = excel_loader.load_rubrics()
            silos = excel_loader.load_learning_outcomes()
    else:
        grades = historical_dataset_loader.load_assessment_results()
        rubrics = historical_dataset_loader.load_rubrics()
        silos = historical_dataset_loader.load_learning_outcomes()

    return {
        "grades": _write_csv(grades, GRADES_COLUMNS, output_dir / "grades.csv"),
        "rubric_comments": _write_csv(
            rubrics, RUBRIC_COLUMNS, output_dir / "rubric_comments.csv"
        ),
        "silo_mappings": _write_csv(silos, SILO_COLUMNS, output_dir / "silo_mappings.csv"),
    }


def main() -> None:
    path = get_settings().historical_dataset_path
    if not path and Path(APPROVED_DATASET).is_file():
        path = APPROVED_DATASET
    written = export_processed(dataset_path=path)
    for name, csv_path in written.items():
        rows = sum(1 for _ in csv_path.open(encoding="utf-8")) - 1
        print(f"{name}: {csv_path} ({rows} rows)")


if __name__ == "__main__":
    main()

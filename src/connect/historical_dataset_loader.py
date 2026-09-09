"""Loads the historical/provided dataset from CSV (N9 fallback path).

This is what IOG-33 ("Source and prepare the provided dataset") actually
feeds. As of this scaffold, `data/sample/` only has small SYNTHETIC files
(no real students) so the pipeline is runnable end-to-end in dev. When
the subject coordinator provides the real historical dataset, drop the
real files in `data/provided/` (create that folder - it's gitignored,
see data/README.md) using the same column names as the sample files, and
switch DATA_DIR below.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Swap to Path(__file__).resolve().parents[2] / "data" / "provided" once
# the real dataset exists. Kept as sample/ so `pytest` and a fresh clone
# both work out of the box with zero setup.
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "sample"


def _load_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Expected dataset files in {DATA_DIR} - "
            "see data/README.md."
        )
    return pd.read_csv(path)


def load_subjects() -> pd.DataFrame:
    return _load_csv("subjects_sample.csv")


def load_learning_outcomes() -> pd.DataFrame:
    return _load_csv("learning_outcomes_sample.csv")


def load_rubrics() -> pd.DataFrame:
    return _load_csv("rubrics_sample.csv")


def load_students() -> pd.DataFrame:
    return _load_csv("students_sample.csv")


def load_assessment_results() -> pd.DataFrame:
    return _load_csv("assessment_results_sample.csv")


def load_topic_materials() -> pd.DataFrame:
    """F9: grounded-citation source passages for the sample dataset.

    Added alongside the excel_loader's own load_topic_materials() - this
    one was missing even though data/sample/topic_materials_sample.csv
    has shipped since Phase 2, which made `python -m src.pipeline` (and
    any full run against sample data, e.g. a fresh clone or a deploy with
    HISTORICAL_DATASET_PATH unset) fail with AttributeError before ever
    reaching the model/estimate stages."""
    return _load_csv("topic_materials_sample.csv")

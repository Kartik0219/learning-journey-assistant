"""End-to-end: `python -m src.pipeline` (Connect -> Parse -> Model -> Estimate).

The stage functions are unit-tested elsewhere; this pins the one command
the Render deploy runs on every boot, so a regression in how the stages
are wired together fails here rather than on the live site.
"""

import pytest

from src import pipeline
from src.connect import historical_dataset_loader as loader
from src.db.database import get_session
from src.db.models import MasteryScore, QuizQuestion, SkillGap, Student, StudyRecommendation
from tests.conftest import _FIXTURE_DATA_DIR


@pytest.fixture
def fixture_dataset(monkeypatch, clean_db):
    monkeypatch.setattr(loader, "DATA_DIR", _FIXTURE_DATA_DIR)


def _counts():
    with get_session() as session:
        return {
            "students": session.query(Student).count(),
            "gaps": session.query(SkillGap).count(),
            "mastery": session.query(MasteryScore).count(),
            "recommendations": session.query(StudyRecommendation).count(),
            "questions": session.query(QuizQuestion).count(),
        }


def test_pipeline_populates_every_stage(fixture_dataset):
    pipeline.run_pipeline()

    counts = _counts()
    assert counts["students"] == 3
    assert counts["gaps"] > 0
    assert counts["mastery"] > 0
    assert counts["recommendations"] == counts["mastery"]


def test_pipeline_is_idempotent_for_gaps_and_scores(fixture_dataset):
    """The deploy re-runs the pipeline on every boot, so a second run must
    not duplicate skill gaps or mastery rows."""
    pipeline.run_pipeline()
    first = _counts()
    pipeline.run_pipeline()
    second = _counts()

    assert second["students"] == first["students"]
    assert second["gaps"] == first["gaps"]
    assert second["mastery"] == first["mastery"]

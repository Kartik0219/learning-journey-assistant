"""Pytest fixtures shared across the test suite.

Sets DATABASE_URL to a throwaway SQLite file *before* anything under
src/ gets imported anywhere in the test session, so tests never touch a
developer's real ljas_dev.db. This only works because conftest.py is
guaranteed to be imported by pytest before test modules are collected -
don't move this import order around.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./ljas_test.db")

import shutil  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from src.connect import historical_dataset_loader as _loader  # noqa: E402
from src.db.database import Base, engine  # noqa: E402
from src.parse.cleaners import run_parse_stage  # noqa: E402

# The small, deterministic dataset the Model/Estimate/Deliver tests were
# written against - three students in one subject (DEMO101), with feedback
# and scores chosen to produce the exact gaps and mastery numbers those
# tests assert (e.g. DEMO0003's positive feedback -> zero gaps -> mastery
# 0.91). It is kept here, separate from the larger data/sample/ demo
# dataset the Render deployment and dashboard use, so the two can evolve
# independently: growing the demo dataset must not silently change the
# numbers the unit tests pin.
_FIXTURE_DATA_DIR = Path(__file__).resolve().parent / "fixtures" / "sample_small"
# DATABASE_URL is sqlite:///./ljas_test.db (set above), i.e. this file,
# relative to the working directory pytest runs from (the repo root).
_TEST_DB_FILE = Path("ljas_test.db")
_SEED_SNAPSHOT_FILE = Path("ljas_test_seed_snapshot.db")


@pytest.fixture
def clean_db():
    """Fresh, empty schema for a single test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def _seed_snapshot():
    """Build the seeded database ONCE per test session and snapshot the
    SQLite file, so the (comparatively slow) Parse stage - CSV load,
    validation, and per-student Fernet encryption - runs a single time
    rather than once per seeded_db test.

    The real `run_parse_stage` is used unchanged; the loader's DATA_DIR is
    just pointed at the small test fixture set for the duration of the
    build, then restored.
    """
    original_dir = _loader.DATA_DIR
    _loader.DATA_DIR = _FIXTURE_DATA_DIR
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        run_parse_stage()
    finally:
        _loader.DATA_DIR = original_dir

    engine.dispose()  # release the file handle so the snapshot can be copied
    shutil.copyfile(_TEST_DB_FILE, _SEED_SNAPSHOT_FILE)
    yield
    _SEED_SNAPSHOT_FILE.unlink(missing_ok=True)


@pytest.fixture
def seeded_db(_seed_snapshot):
    """A fresh copy of the seeded database for a single test.

    Restores the pristine snapshot built by `_seed_snapshot` before each
    test, so every test sees the same Connect+Parse starting state -
    subjects, SILOs, rubrics, students (DEMO0001-3), assessment results,
    topic materials, plus seeded consent and demo sign-in credentials -
    and any rows a test adds (skill gaps, mastery scores, quiz questions
    it generates itself) are discarded at the next restore. The
    Model/Estimate stages are deliberately NOT pre-run, so tests drive
    those themselves and pre-estimate assertions (mastery is None until
    computed) stay valid.
    """
    engine.dispose()
    shutil.copyfile(_SEED_SNAPSHOT_FILE, _TEST_DB_FILE)
    yield
    # Reset to an empty schema so this test's seeded rows can't leak into a
    # later test that reuses the same shared SQLite file (e.g. a clean_db
    # test that assumes it starts empty).
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

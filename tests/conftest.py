"""Pytest fixtures shared across the test suite.

Sets DATABASE_URL to a throwaway SQLite file *before* anything under
src/ gets imported anywhere in the test session, so tests never touch a
developer's real ljas_dev.db. This only works because conftest.py is
guaranteed to be imported by pytest before test modules are collected -
don't move this import order around.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./ljas_test.db")

import pytest  # noqa: E402

from src.db.database import Base, engine  # noqa: E402


@pytest.fixture
def clean_db():
    """Fresh, empty schema for a single test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

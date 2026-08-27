"""Read-only Moodle Web Services client (F1).

F1: "Import learning outcomes, topic materials, rubrics, results and
written feedback from the historical subject dataset and from Moodle
(read-only Web Services access)."

This is intentionally a thin wrapper, not a full Moodle SDK - Moodle's
REST-ish `webservice/rest/server.php` endpoint takes a `wstoken`,
`wsfunction`, and `moodlewsrestformat=json`, and every call below just
shapes that request. No write-capable wsfunction should ever be added
here (F12: never write back to Moodle).

Until MOODLE_WS_TOKEN is actually issued (ask the subject coordinator /
La Trobe IT for the team's Moodle Web Services token), every method here
raises MoodleNotConfiguredError. Callers should catch that and fall back
to src.connect.historical_dataset_loader, per N9 ("If the live Moodle
connection is delayed, run the same pipeline on the historical
dataset.").
"""

from __future__ import annotations

from typing import Any

import requests

from src.common.logging_config import get_logger
from src.config import get_settings

logger = get_logger(__name__)


class MoodleNotConfiguredError(RuntimeError):
    """Raised when Moodle credentials aren't set yet (expected in dev)."""


class MoodleClient:
    def __init__(self) -> None:
        self._settings = get_settings()

    def _call(self, ws_function: str, **params: Any) -> Any:
        if not self._settings.moodle_configured:
            raise MoodleNotConfiguredError(
                "MOODLE_BASE_URL / MOODLE_WS_TOKEN are not set - see .env.example. "
                "Use src.connect.historical_dataset_loader instead (N9 fallback)."
            )

        url = f"{self._settings.moodle_base_url}/webservice/rest/server.php"
        query = {
            "wstoken": self._settings.moodle_ws_token,
            "wsfunction": ws_function,
            "moodlewsrestformat": "json",
            **params,
        }
        logger.info("Calling Moodle wsfunction=%s", ws_function)
        response = requests.get(url, params=query, timeout=30)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and data.get("exception"):
            # Moodle returns 200 OK with an "exception" body on WS errors.
            raise RuntimeError(f"Moodle WS error calling {ws_function}: {data}")
        return data

    # --- Read-only calls used by F1. Fill in the real wsfunction names /
    # response shapes once the team has an actual Moodle WS token to test
    # against - these are placeholders for the expected shape. ---

    def get_courses(self) -> Any:
        return self._call("core_course_get_courses")

    def get_course_grades(self, course_id: int) -> Any:
        return self._call("gradereport_user_get_grade_items", courseid=course_id)

    def get_assignments(self, course_ids: list[int]) -> Any:
        return self._call("mod_assign_get_assignments", **{"courseids[0]": course_ids[0]})

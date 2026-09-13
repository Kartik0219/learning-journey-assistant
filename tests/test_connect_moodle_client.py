"""F1/F12/N9: the read-only Moodle Web Services client.

There is no live Moodle instance or WS token available to this project, so
these tests pin the client's contract against a stubbed HTTP layer instead:
what it sends, how it reports Moodle's errors, that it refuses to run
without credentials (the N9 fallback trigger), and that it only ever calls
read-only wsfunctions (F12).
"""

import pytest

from src.connect import moodle_client
from src.connect.moodle_client import MoodleClient, MoodleNotConfiguredError


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise moodle_client.requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


@pytest.fixture
def moodle_env(monkeypatch):
    monkeypatch.setenv("MOODLE_BASE_URL", "https://moodle.example.edu")
    monkeypatch.setenv("MOODLE_WS_TOKEN", "test-token")


class _CallLog(list):
    """The recorded requests, plus the canned response the fake returns."""

    payload = []
    status_code = 200


@pytest.fixture
def captured_calls(monkeypatch):
    calls = _CallLog()

    def fake_get(url, params=None, timeout=None):
        calls.append({"url": url, "params": params, "timeout": timeout})
        return _FakeResponse(calls.payload, calls.status_code)

    monkeypatch.setattr(moodle_client.requests, "get", fake_get)
    return calls


def test_unconfigured_client_raises_so_callers_fall_back(monkeypatch, captured_calls):
    monkeypatch.delenv("MOODLE_BASE_URL", raising=False)
    monkeypatch.delenv("MOODLE_WS_TOKEN", raising=False)

    with pytest.raises(MoodleNotConfiguredError):
        MoodleClient().get_courses()
    assert captured_calls == []  # no network traffic without credentials


def test_request_shape_uses_rest_endpoint_token_and_json(moodle_env, captured_calls):
    captured_calls.payload = [{"id": 7, "shortname": "CSE1OOF"}]

    courses = MoodleClient().get_courses()

    assert courses == [{"id": 7, "shortname": "CSE1OOF"}]
    call = captured_calls[0]
    assert call["url"] == "https://moodle.example.edu/webservice/rest/server.php"
    assert call["params"]["wstoken"] == "test-token"
    assert call["params"]["wsfunction"] == "core_course_get_courses"
    assert call["params"]["moodlewsrestformat"] == "json"
    assert call["timeout"] == 30


def test_course_scoped_calls_pass_their_ids(moodle_env, captured_calls):
    client = MoodleClient()
    client.get_course_grades(42)
    client.get_assignments([42, 43])

    assert captured_calls[0]["params"]["courseid"] == 42
    assert captured_calls[1]["params"]["courseids[0]"] == 42


def test_moodle_exception_body_is_raised_not_returned(moodle_env, captured_calls):
    # Moodle reports WS errors as HTTP 200 with an "exception" body.
    captured_calls.payload = {"exception": "invalid_token", "errorcode": "invalidtoken"}

    with pytest.raises(RuntimeError, match="core_course_get_courses"):
        MoodleClient().get_courses()


def test_http_error_propagates(moodle_env, captured_calls):
    captured_calls.status_code = 503

    with pytest.raises(moodle_client.requests.HTTPError):
        MoodleClient().get_courses()


def test_client_only_calls_read_only_wsfunctions(moodle_env, captured_calls):
    """F12: never write back to Moodle. Every wsfunction the client can
    call must be a read (get_*) - a create/update/delete/submit function
    appearing here is a requirement breach, not a feature."""
    client = MoodleClient()
    client.get_courses()
    client.get_course_grades(1)
    client.get_assignments([1])

    for call in captured_calls:
        name = call["params"]["wsfunction"]
        assert "_get_" in name, name
        for verb in ("create", "update", "delete", "save", "submit", "set_", "add_"):
            assert verb not in name, name

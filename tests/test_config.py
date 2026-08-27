from src.config import get_settings


def test_default_database_url_is_local_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = get_settings()
    assert settings.database_url.startswith("sqlite:///")


def test_moodle_not_configured_by_default(monkeypatch):
    monkeypatch.delenv("MOODLE_BASE_URL", raising=False)
    monkeypatch.delenv("MOODLE_WS_TOKEN", raising=False)
    settings = get_settings()
    assert settings.moodle_configured is False


def test_moodle_configured_when_both_set(monkeypatch):
    monkeypatch.setenv("MOODLE_BASE_URL", "https://example.moodle.test")
    monkeypatch.setenv("MOODLE_WS_TOKEN", "fake-token")
    settings = get_settings()
    assert settings.moodle_configured is True

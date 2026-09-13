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


def test_historical_dataset_path_unset_by_default(monkeypatch):
    """IOG-33/N9: unset means "use the synthetic sample data" - same
    fallback pattern as Moodle above."""
    monkeypatch.delenv("HISTORICAL_DATASET_PATH", raising=False)
    monkeypatch.delenv("RENDER", raising=False)
    settings = get_settings()
    assert settings.historical_dataset_path is None


def test_render_defaults_to_the_approved_dataset(monkeypatch):
    """Render ignores render.yaml env vars on an existing service, so the live
    demo falls back to the committed 150-student workbook by itself."""
    from src.config import APPROVED_DATASET

    monkeypatch.delenv("HISTORICAL_DATASET_PATH", raising=False)
    monkeypatch.setenv("RENDER", "true")
    assert get_settings().historical_dataset_path == APPROVED_DATASET


def test_explicit_dataset_path_wins_on_render(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("HISTORICAL_DATASET_PATH", "data/provided/other.xlsx")
    assert get_settings().historical_dataset_path == "data/provided/other.xlsx"


def test_historical_dataset_path_set_when_env_var_present(monkeypatch):
    monkeypatch.setenv("HISTORICAL_DATASET_PATH", "data/provided/real.xlsx")
    settings = get_settings()
    assert settings.historical_dataset_path == "data/provided/real.xlsx"

"""Central settings, loaded from environment variables / .env.

Everything that could plausibly be a secret or an environment-specific
value (DB connection string, API tokens) lives here and nowhere else -
see requirement N3 ("Do not keep passwords or API keys in the source
code.") Never hardcode a real value as a default; use safe local-dev
defaults only (e.g. the SQLite path).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # no-op if .env doesn't exist (e.g. in CI)


@dataclass(frozen=True)
class Settings:
    database_url: str
    moodle_base_url: str | None
    moodle_ws_token: str | None
    historical_dataset_path: str | None
    llm_provider: str | None
    llm_api_key: str | None
    app_secret_key: str
    encryption_key: str
    log_level: str

    @property
    def moodle_configured(self) -> bool:
        """True once real Moodle credentials are supplied.

        Until then, src/connect falls back to the historical dataset
        (requirement N9), which is the expected state for most of Phase 1
        development.
        """
        return bool(self.moodle_base_url and self.moodle_ws_token)


def get_settings() -> Settings:
    """Build a Settings object from the current environment.

    Not cached at import time on purpose - tests override env vars per-case
    and expect a fresh read.
    """
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./ljas_dev.db"),
        moodle_base_url=os.getenv("MOODLE_BASE_URL") or None,
        moodle_ws_token=os.getenv("MOODLE_WS_TOKEN") or None,
        # IOG-33/N9: path to the real provided .xlsx dataset (data/provided/,
        # gitignored - never commit real student records). Unset in CI/a
        # fresh clone, so src.parse.cleaners falls back to the synthetic
        # data/sample/ CSVs automatically - same fallback pattern as Moodle.
        historical_dataset_path=os.getenv("HISTORICAL_DATASET_PATH") or None,
        llm_provider=os.getenv("LLM_PROVIDER") or None,
        llm_api_key=os.getenv("LLM_API_KEY") or None,
        app_secret_key=os.getenv("APP_SECRET_KEY", "changeme-dev-only"),
        # N3: dev-only fallback so `pytest`/local runs work with zero setup.
        # This is a real, valid Fernet key - fine for local dev, but every
        # non-dev environment must set its own via `Fernet.generate_key()`
        # (see .env.example) and never commit that value.
        encryption_key=os.getenv(
            "ENCRYPTION_KEY", "XOcjJUrnSvGw5MrTuZKQ0hxBhnlPk5yjxyQuKnyxFJY="
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

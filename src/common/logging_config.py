"""Shared logging setup.

This is deliberately generic application logging, not the security/audit
log required by N4 ("Keep a log of sign-in, consent changes, data import,
and creation of study plans and quizzes."). That audit trail is a distinct,
tamper-evident record tied to the AuditLogEntry model in src/db/models.py
and is Phase 5 scope (IOG-42) - don't conflate the two when building that
ticket out.
"""

from __future__ import annotations

import logging

from src.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

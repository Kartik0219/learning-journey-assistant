"""Learning Journey Assistant.

Package layout follows the five-stage pipeline committed to in the tender
document (requirement N7): Connect -> Parse -> Model -> Estimate -> Deliver.

    src/connect/   Pull data in (Moodle API + historical dataset fallback)
    src/parse/     Clean, validate, and match records across sources
    src/model/     Skill-gap extraction, SILO mapping, embeddings (Phase 3)
    src/estimate/  Mastery scoring, study recommendations, quizzes (Phase 4)
    src/deliver/   Student-facing dashboard / API (Phase 4/6)
    src/db/        Shared database models and session handling
    src/common/    Cross-cutting utilities (config, logging)

Phase 1 (this scaffold) builds the environment, the shared database schema,
and the Connect/Parse groundwork. The `model`, `estimate`, and `deliver`
packages are left as thin stubs with docstrings pointing at the Jira ticket
that owns filling them in, so the folders exist and imports don't break for
whoever picks those tickets up next.
"""

"""Phase 4 (IOG-38 continued, IOG-39, IOG-30/IOG-41 testing) - not yet
implemented.

Owns:
  - Weighted mastery calculation per student per SILO (F6), writing
    MasteryScore rows with `explanation_text` populated - F6 requires
    the score to be "explainable from the evidence", so this can't be a
    black-box number with no reasoning attached.
  - Recommending a study method from the fixed table (retrieval practice
    / spaced practice / worked examples) based on gap type (F7) - the
    LLM only writes the explanation for the student, it does not choose
    the method itself.
  - Generating adaptive practice quizzes, checked against subject
    materials before being shown (F8).
  - Storing quiz answers / plan usage and feeding that back into mastery
    estimates (F11).

Depends on src.model.silo_mapping existing first (needs SkillGap rows
with severity/confidence to weight against).
"""


def calculate_mastery_score(*args, **kwargs):
    """Placeholder entry point - implement as part of IOG-38/IOG-39."""
    raise NotImplementedError(
        "Phase 4 hasn't started. See this module's docstring for scope."
    )


def recommend_study_method(*args, **kwargs):
    """Placeholder entry point - implement as part of IOG-39."""
    raise NotImplementedError(
        "Phase 4 hasn't started. See this module's docstring for scope."
    )

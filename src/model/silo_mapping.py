"""Phase 3 (IOG-37, IOG-38) - not yet implemented.

Owns:
  - AI-based extraction of skill gaps from rubric/marker feedback (F3, F4),
    writing SkillGap rows (src/db/models.py) with source_evidence_text,
    severity, and confidence populated - never guess a value for
    confidence, and anything below the team's agreed threshold must be
    left with reviewed=False rather than shown to students (F4).
  - Linking gaps to learning outcomes + subject material passages via
    text embeddings and similarity scores (F5, F9).
  - Weighted mastery scoring lives in src/estimate/mastery.py, not here -
    this module's job stops at "what's the gap and what SILO/resource
    does it relate to", not "how good is the student at that SILO".

N5 applies directly to this module: rubric/feedback text is untrusted
input to whatever LLM call goes here. Keep it in the data slot of the
prompt, never concatenate it into an instruction, and validate the
model's output against an expected schema before writing it to SkillGap
(reject and log, don't silently accept malformed output).
"""

def extract_skill_gaps(*args, **kwargs):
    """Placeholder entry point - implement as part of IOG-37."""
    raise NotImplementedError(
        "Phase 3 (IOG-37) hasn't started. See this module's docstring for scope."
    )


def map_gap_to_learning_outcome(*args, **kwargs):
    """Placeholder entry point - implement as part of IOG-38."""
    raise NotImplementedError(
        "Phase 3 (IOG-38) hasn't started. See this module's docstring for scope."
    )

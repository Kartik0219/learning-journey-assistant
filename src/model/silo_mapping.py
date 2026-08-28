"""Phase 3 (IOG-37, IOG-38): AI-based skill-gap extraction and SILO
mapping.

Owns:
  - AI-based extraction of skill gaps from rubric/marker feedback (F3,
    F4), writing SkillGap rows (src/db/models.py) with
    source_evidence_text, severity, and confidence populated.
  - Linking gaps to learning outcomes via text-embedding similarity
    scores (F5).

Weighted mastery scoring lives in src/estimate/mastery.py, not here -
this module's job stops at "what's the gap and what SILO does it
relate to", not "how good is the student at that SILO".

## Why TF-IDF, not a hosted LLM

This environment has no LLM API credentials configured, and the tender
requires open-source/free-tier tooling with no procurement dependency
(Section 2.5) and explicitly worries about generated output being
"hallucinated" rather than grounded (Section 2.4). TF-IDF cosine
similarity - scikit-learn, fully local, no network call - is a genuine
text-embedding technique (F5 asks for "text embeddings and similarity
scores", not specifically a neural embedding model) and has a property
an LLM call wouldn't automatically give us: every gap's confidence
score and every SILO link is a deterministic, reproducible number you
can point at and explain, which is exactly what F4 and F6 ask for. If
the team later gets a real LLM budget, `extract_skill_gaps` is the one
function to swap - `map_gap_to_learning_outcome`'s similarity approach
can stay as-is even then, since F5 asks for similarity-based linking
specifically.

## N5 (untrusted input)

Feedback and rubric text are untrusted input. This module never
concatenates that text into an instruction to a model - there is no
model call at all, only vectorisation and cosine similarity, so there
is no instruction-following surface for the untrusted text to attack.
Every extracted gap's source_evidence_text is a verbatim quote of the
feedback clause it came from - nothing is written into the database
that wasn't literally present in the input.
"""

from __future__ import annotations

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from src.db.models import AssessmentResult, LearningOutcome, RubricCriterion, SkillGap

# F4: below this confidence a gap is held for review, never shown to a
# student, per "items with low confidence are held for review and are
# not shown to the student until checked."
CONFIDENCE_REVIEW_THRESHOLD = 0.15

# F5: below this similarity a gap is left unmapped rather than forced
# onto the closest-but-still-unrelated learning outcome.
LO_MAPPING_THRESHOLD = 0.08

# Deliberately simple, explainable lexicon rather than a black-box
# classifier - appropriate to the tender's "demonstration-level
# functionality" scope (Section 4.3). A clause matching none of these
# is treated as positive/neutral feedback and produces no gap - this is
# what makes wholly positive feedback (e.g. "Excellent application...")
# correctly yield zero gaps instead of one for every sentence.
DEFICIENCY_MARKERS: tuple[str, ...] = (
    "minor error", "error", "incorrect", "vague", "unclear", "missing",
    "lacks", "lacking", "insufficient", "fails to", "failed to",
    "did not", "didn't", "no ", "not discussed", "not addressed",
)
LOW_SEVERITY_MARKERS: tuple[str, ...] = ("minor error", "small error", "slight", "slightly")
HIGH_SEVERITY_MARKERS: tuple[str, ...] = (
    "major error", "significant", "completely incorrect", "fails to", "failed to",
)

_CLAUSE_SPLIT = re.compile(r"[.;!]")
_CONNECTIVE_SPLIT = re.compile(r"\s*,?\s*\b(?:but|however|although|and)\b\s*", re.IGNORECASE)


def _split_into_clauses(feedback_text: str) -> list[str]:
    """Break feedback into short, citable clauses.

    Deliberately simple (punctuation + connective-word splitting, no
    real parser) - this is a heuristic, not a robust NLP pipeline, which
    is why every downstream gap still carries its exact source clause
    for a human to check (F4) rather than being trusted blindly.
    """
    clauses: list[str] = []
    for sentence in _CLAUSE_SPLIT.split(feedback_text):
        sentence = sentence.strip()
        if not sentence:
            continue
        for clause in _CONNECTIVE_SPLIT.split(sentence):
            clause = clause.strip()
            if clause:
                clauses.append(clause)
    return clauses


def _severity_for(clause_lower: str) -> str:
    if any(marker in clause_lower for marker in HIGH_SEVERITY_MARKERS):
        return "high"
    if any(marker in clause_lower for marker in LOW_SEVERITY_MARKERS):
        return "low"
    return "medium"


def best_similarity(candidate: str, corpus: list[str]) -> tuple[int, float]:
    """Index and cosine-similarity score of the corpus entry closest to
    `candidate`. Returns (-1, 0.0) if the corpus is empty or every
    similarity is exactly zero (no shared vocabulary at all)."""
    if not corpus:
        return -1, 0.0
    # Character n-grams, not word tokens: feedback rarely echoes rubric
    # wording exactly ("applied" vs "apply", "technique" vs
    # "techniques"), and word-level TF-IDF treats those as unrelated
    # tokens with zero overlap. Character n-grams still reward the
    # shared root ("appli...", "techniq...") without needing a stemmer
    # dependency.
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
    try:
        matrix = vectorizer.fit_transform([candidate, *corpus])
    except ValueError:
        # Empty vocabulary after stop-word removal (e.g. very short text).
        return -1, 0.0
    similarities = cosine_similarity(matrix[0:1], matrix[1:])[0]
    best_index = int(similarities.argmax())
    return best_index, float(similarities[best_index])


def extract_skill_gaps(session: Session, assessment_result: AssessmentResult) -> list[SkillGap]:
    """F3/F4: extract skill-gap candidates from one assessment result's
    written feedback, citing the exact feedback clause as evidence.

    Confidence is the cosine similarity between the gap's evidence
    clause and the closest rubric criterion for the assessment's
    subject - the more specifically the feedback lines up with a named,
    evaluated criterion, the more confident the extraction. Gaps below
    CONFIDENCE_REVIEW_THRESHOLD are written with reviewed=False and must
    not be surfaced to the student (enforced in src.deliver.app).
    """
    if not assessment_result.feedback_text:
        return []

    subject = assessment_result.assessment.subject
    criteria: list[RubricCriterion] = [
        criterion for rubric in subject.rubrics for criterion in rubric.criteria
    ]
    criteria_texts = [c.criterion_text for c in criteria]

    gaps: list[SkillGap] = []
    for clause in _split_into_clauses(assessment_result.feedback_text):
        clause_lower = clause.lower()
        if not any(marker in clause_lower for marker in DEFICIENCY_MARKERS):
            continue  # positive/neutral clause - not a gap

        _, confidence = best_similarity(clause, criteria_texts)
        gap = SkillGap(
            assessment_result_id=assessment_result.id,
            source_evidence_text=clause,
            severity=_severity_for(clause_lower),
            confidence=round(confidence, 4),
            reviewed=confidence >= CONFIDENCE_REVIEW_THRESHOLD,
        )
        session.add(gap)
        session.flush()
        gaps.append(gap)

    return gaps


def map_gap_to_learning_outcome(session: Session, gap: SkillGap) -> LearningOutcome | None:
    """F5: link a skill gap to the learning outcome its evidence text is
    closest to, by TF-IDF cosine similarity against every learning
    outcome description in the gap's subject. Leaves the gap unmapped
    (learning_outcome_id stays None) rather than forcing a weak match
    onto the closest-but-unrelated outcome.

    Also sets `gap_type` from the matched outcome's verb, for
    src.estimate.mastery.recommend_study_method's fixed table (F7).
    """
    subject = gap.assessment_result.assessment.subject
    outcomes = list(subject.learning_outcomes)
    descriptions = [o.description for o in outcomes]

    best_index, similarity = best_similarity(gap.source_evidence_text, descriptions)
    if best_index == -1 or similarity < LO_MAPPING_THRESHOLD:
        return None

    outcome = outcomes[best_index]
    gap.learning_outcome_id = outcome.id
    gap.gap_type = gap_type_for(outcome.description)
    session.flush()
    return outcome


def gap_type_for(learning_outcome_description: str) -> str:
    """Classify a gap by the verb of the learning outcome it maps to -
    the same fixed, deterministic rule src.estimate.mastery reads back
    to pick a study method (F7)."""
    text = learning_outcome_description.lower()
    if text.startswith("apply") or " apply " in text:
        return "application"
    if "evaluat" in text or "critical" in text:
        return "evaluation"
    return "conceptual"

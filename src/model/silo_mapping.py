"""Phase 3 (IOG-37, IOG-38): AI-based skill-gap extraction and SILO
mapping.

Owns:
  - Extraction of skill gaps, writing SkillGap rows (src/db/models.py)
    with source_evidence_text, severity, and confidence populated. Two
    extraction paths, chosen per assessment result by whether
    silo_tags_text is set (see "Two extraction paths" below).
  - Linking gaps to learning outcomes (F5): an exact SILO-code match
    first when the gap carries one, text-embedding similarity
    otherwise.

## Two extraction paths (Phase 6/IOG-33)

The original design assumed every dataset would need feedback-text
mining to *infer* which SILO a deficiency relates to. The real provided
dataset (`CSE_results_150_students_3_Subjects.xlsx`, loaded via
src.connect.excel_loader) doesn't need inference at all: its "SILO's"
column already states, per result, exactly which learning outcomes that
result covers - explicit institutional ground truth, not a guess. Its
feedback text is also templated boilerplate ("Assessment marked
according to rubric...") that the old DEFICIENCY_MARKERS keyword
heuristic never matches, which is why running that heuristic against
this dataset extracted 0 gaps from 1,650 results.

So extraction now branches on `assessment_result.silo_tags_text`:
  - Set (real dataset): `_extract_from_silo_tags` - one gap per tagged
    SILO where the result's score falls below MASTERY_THRESHOLD,
    severity from the score band, confidence 1.0 (it's a stated fact
    about the result, not an inference), source_evidence_text the
    verbatim "SILOn: description" tag.
  - Unset (synthetic sample dataset, which has no SILO-tag column):
    `_extract_from_feedback_text` - the original TF-IDF/keyword-marker
    heuristic, unchanged, so tests/test_model_silo_mapping.py's existing
    expectations keep passing exactly as before.

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

from src.connect.excel_loader import parse_silo_tags
from src.db.models import AssessmentResult, LearningOutcome, RubricCriterion, SkillGap

# F4: below this confidence a gap is held for review, never shown to a
# student, per "items with low confidence are held for review and are
# not shown to the student until checked."
CONFIDENCE_REVIEW_THRESHOLD = 0.15

# F5: below this similarity a gap is left unmapped rather than forced
# onto the closest-but-still-unrelated learning outcome.
LO_MAPPING_THRESHOLD = 0.08

# Real-dataset path (IOG-33): a result at or above this score is treated
# as mastery of every SILO it's tagged with - no gap is recorded for it.
# Below it, a gap is recorded per tagged SILO with severity from the
# score band below. 80 lines up with the dataset's own HD/D boundary
# (empirically: At risk <50, P 50-59.99, C 60-69.99, D/HD 70-79.99/80+) -
# a High Distinction result isn't a "skill gap" by any reasonable read.
MASTERY_THRESHOLD = 80.0

# Real-dataset path: the tagged SILO's severity is derived from the
# score itself (an explicit institutional number), not guessed from
# feedback wording - collapses the dataset's four sub-mastery grade
# bands (At risk / P / C / D) into three severities, matching the
# vocabulary the sample-dataset heuristic already uses below.
_SCORE_HIGH_SEVERITY_MAX = 50.0  # < 50 ("At risk") -> high
_SCORE_MEDIUM_SEVERITY_MAX = 70.0  # 50-69.99 ("P"/"C") -> medium; else ("D") -> low

# Real-dataset path: an explicit institutional SILO tag is a stated fact
# about the result, not an inference - full confidence, always reviewed.
SILO_TAG_CONFIDENCE = 1.0

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


def _severity_for_score(score: float) -> str:
    """Real-dataset path: map a 0-100 score to a gap severity band. Only
    called for scores already known to be below MASTERY_THRESHOLD."""
    if score < _SCORE_HIGH_SEVERITY_MAX:
        return "high"
    if score < _SCORE_MEDIUM_SEVERITY_MAX:
        return "medium"
    return "low"


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
    """F3/F4: extract skill-gap candidates for one assessment result.

    Dispatches on whether the result carries explicit SILO tags (the
    real dataset, via src.connect.excel_loader) or not (the synthetic
    sample dataset) - see the module docstring's "Two extraction paths".
    """
    if assessment_result.silo_tags_text:
        return _extract_from_silo_tags(session, assessment_result)
    return _extract_from_feedback_text(session, assessment_result)


def _extract_from_silo_tags(
    session: Session, assessment_result: AssessmentResult
) -> list[SkillGap]:
    """Real-dataset path (IOG-33): one gap per SILO tagged on this result,
    provided the result's score is below MASTERY_THRESHOLD. No
    feedback-text mining at all - the tag is already the answer to "what
    SILO does this relate to", and the score is already the answer to
    "how severe". source_evidence_text is the literal "SILOn:
    description" tag (N5: nothing paraphrased)."""
    score = assessment_result.score
    if score is None or score >= MASTERY_THRESHOLD:
        return []

    severity = _severity_for_score(score)
    gaps: list[SkillGap] = []
    for silo_code, description in parse_silo_tags(assessment_result.silo_tags_text):
        gap = SkillGap(
            assessment_result_id=assessment_result.id,
            source_evidence_text=f"{silo_code}: {description}",
            severity=severity,
            confidence=SILO_TAG_CONFIDENCE,
            reviewed=True,
        )
        session.add(gap)
        session.flush()
        gaps.append(gap)

    return gaps


def _extract_from_feedback_text(
    session: Session, assessment_result: AssessmentResult
) -> list[SkillGap]:
    """Sample-dataset path (original F3/F4 heuristic, unchanged):
    keyword-marker clause splitting + TF-IDF confidence against the
    subject's rubric criteria. See the module docstring for why this
    stays TF-IDF rather than a hosted LLM."""
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
    """F5: link a skill gap to a learning outcome in its subject.

    Tries an exact SILO-code match first (source_evidence_text starts
    with "SILOn:", which is only true for the real-dataset extraction
    path in `_extract_from_silo_tags` - the tag names its own SILO code,
    so matching it exactly is strictly more reliable than any similarity
    score). Falls back to TF-IDF cosine similarity against every
    learning outcome description in the gap's subject otherwise (the
    sample-dataset path, unchanged), leaving the gap unmapped
    (learning_outcome_id stays None) rather than forcing a weak match
    onto the closest-but-unrelated outcome.

    Also sets `gap_type` from the matched outcome's verb, for
    src.estimate.mastery.recommend_study_method's fixed table (F7).
    """
    subject = gap.assessment_result.assessment.subject
    outcomes = list(subject.learning_outcomes)

    exact = _match_by_silo_code(outcomes, gap.source_evidence_text)
    if exact is not None:
        gap.learning_outcome_id = exact.id
        gap.gap_type = gap_type_for(exact.description)
        session.flush()
        return exact

    descriptions = [o.description for o in outcomes]
    best_index, similarity = best_similarity(gap.source_evidence_text, descriptions)
    if best_index == -1 or similarity < LO_MAPPING_THRESHOLD:
        return None

    outcome = outcomes[best_index]
    gap.learning_outcome_id = outcome.id
    gap.gap_type = gap_type_for(outcome.description)
    session.flush()
    return outcome


def _match_by_silo_code(
    outcomes: list[LearningOutcome], source_evidence_text: str
) -> LearningOutcome | None:
    """Extract a leading "SILOn:" code from evidence text (as written by
    `_extract_from_silo_tags`) and find the outcome with that exact code
    in this subject. Returns None for sample-dataset evidence text
    (plain feedback clauses never start with "SILOn:") so that path
    falls through to similarity matching unchanged."""
    match = re.match(r"\s*(SILO\d+)\s*:", source_evidence_text, re.IGNORECASE)
    if not match:
        return None
    code = match.group(1).upper()
    return next((o for o in outcomes if o.code.upper() == code), None)


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

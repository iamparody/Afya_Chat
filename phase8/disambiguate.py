"""
Phase 8 — Disambiguation loop core logic.

Three functions consumed by the Streamlit app (phase6/app.py) and the
planned CLI runner (phase8/run_disambiguation.py).

None of these functions call the RAG pipeline — they operate on the
validated result dict returned by phase5/rag.run().

Design spec (updated 2026-09-17):
  - Ambiguity trigger: score_margin between candidate #1 and #2 is below
    AMBIGUITY_MARGIN_THRESHOLD (deterministic Python — independent of LLM confidence).
    A HIGH-confidence leading candidate can still be ambiguous if the margin is narrow.
  - Pairwise discriminator: get_discriminating_questions() finds missing_information
    items that differ between the top-2 candidates by score rank (not confidence tier).
    Disambiguation is only triggered when at least one discriminating question exists.
  - Max rounds: MAX_ROUNDS = 3. Caller is responsible for the counter.
  - Enrichment: free text appended to the original presentation string.
"""

import re

# Sync with phase5/rag.py AMBIGUITY_MARGIN_THRESHOLD — calibrate from Step 1 log distributions.
AMBIGUITY_MARGIN_THRESHOLD = 0.15

MAX_ROUNDS = 3

_STOPWORDS = frozenset({"or", "and", "the", "a", "an", "of", "for", "with", "in", "is", "are", "has", "no", "not"})


def _key_words(s: str) -> frozenset:
    tokens = re.sub(r"[^\w\s]", "", s.lower()).split()
    return frozenset(t.rstrip("s") for t in tokens if t not in _STOPWORDS)


def _dedup_questions(questions: list) -> list:
    """Drop longer questions whose key concepts are fully covered by a shorter one."""
    keep = []
    for i, q in enumerate(questions):
        q_kw = _key_words(q)
        redundant = any(
            i != j
            and _key_words(questions[j]) <= q_kw
            and len(questions[j]) < len(q)
            for j in range(len(questions))
        )
        if not redundant:
            keep.append(q)
    return keep


def is_ambiguous(result: dict) -> bool:
    """
    Returns True when the result warrants a follow-up question round.

    Ambiguity is determined by the deterministic score margin between candidate
    #1 and #2 (attached to result as _score_margin by rag.run()), independently
    of LLM-assigned confidence. A HIGH-confidence leading candidate can still be
    ambiguous if the margin is narrow.

    Disambiguation is only triggered when a usable pairwise discriminator also
    exists — the caller is expected to check get_discriminating_questions() before
    presenting questions to the user.

    Falls back to the original confidence-tier check if _score_margin is absent
    (e.g. results from older pipeline versions or test fixtures).
    """
    candidates = result.get("candidates", [])
    if len(candidates) < 2:
        return False

    score_margin = result.get("_score_margin")

    if score_margin is not None:
        return score_margin < AMBIGUITY_MARGIN_THRESHOLD

    # Legacy fallback: confidence-tier check (pre-Step 3 results)
    leading = result.get("leading_candidate", "")
    leading_confidence = None
    for c in candidates:
        if c["diagnosis"] == leading:
            leading_confidence = c.get("confidence_level")
            break

    if leading_confidence == "high":
        return False

    tier_count = sum(
        1 for c in candidates
        if c.get("confidence_level") == leading_confidence
    )
    return tier_count >= 2


def get_discriminating_questions(result: dict) -> list:
    """
    Returns missing_information strings that discriminate between the top-2
    candidates by score rank (candidates[0] and candidates[1]).

    Logic:
      1. Take the top-2 candidates by position (score rank, not confidence tier).
      2. Collect their missing_information sets.
      3. Keep only items present in SOME but not ALL of the top-2 — these
         are the features that differ between the two possibilities and are
         therefore worth asking about.
      4. Items shared by both candidates are non-discriminating (asking won't
         break the tie).

    Returns an empty list if fewer than 2 candidates exist or if all
    missing_information items are shared between the top-2.
    """
    candidates = result.get("candidates", [])
    if len(candidates) < 2:
        return []

    top_2 = candidates[:2]

    missing_per_candidate = [
        set(c.get("missing_information", []))
        for c in top_2
    ]

    all_missing = set().union(*missing_per_candidate)
    shared = set.intersection(*missing_per_candidate)
    discriminating = _dedup_questions(sorted(all_missing - shared))

    return discriminating


def enrich_presentation(presentation: str, answers: dict) -> str:
    """
    Appends answered follow-up questions to the presentation string.

    answers: {question_text: answer_text}
    Skipped or blank answers are ignored.

    The enriched string is passed back into phase5/rag.run() for the
    next disambiguation round.
    """
    additions = []
    for question, answer in answers.items():
        if answer and answer.strip():
            additions.append(f"{question}: {answer.strip()}")

    if not additions:
        return presentation

    enriched = presentation.rstrip(". ")
    enriched += ". " + ". ".join(additions) + "."
    return enriched

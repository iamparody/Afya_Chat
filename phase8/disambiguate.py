"""
Phase 8 — Disambiguation loop core logic.

Three functions consumed by the Streamlit app (phase6/app.py) and the
planned CLI runner (phase8/run_disambiguation.py).

None of these functions call the RAG pipeline — they operate on the
validated result dict returned by phase5/rag.run().

Design spec (PF-4):
  - Ambiguity trigger: no high-confidence candidate AND ≥2 candidates
    share the same (non-high) confidence tier.
  - Question selection: missing_information items that appear in SOME
    but not ALL tied candidates — these discriminate between the tied
    set. Items shared by all tied candidates are not discriminating.
  - Max rounds: MAX_ROUNDS = 3. Caller is responsible for the counter.
  - Enrichment: free text appended to the original presentation string.
"""

import re

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

    Trigger: leading candidate is not high-confidence AND at least two
    candidates share the same confidence tier as the leading candidate.
    """
    candidates = result.get("candidates", [])
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
    Returns a list of missing_information strings that discriminate
    between the tied top-tier candidates.

    Logic:
      1. Find all candidates sharing the leading confidence tier.
      2. Collect their missing_information sets.
      3. Keep only items present in SOME but not ALL tied candidates —
         these are the features that differ between possibilities and
         are therefore worth asking about.
      4. Items missing from ALL tied candidates are non-discriminating
         (asking won't break the tie).

    Returns an empty list if there are no tied candidates or if all
    missing_information items are shared across all tied candidates.
    """
    candidates = result.get("candidates", [])
    leading = result.get("leading_candidate", "")

    leading_confidence = None
    for c in candidates:
        if c["diagnosis"] == leading:
            leading_confidence = c.get("confidence_level")
            break

    tied = [
        c for c in candidates
        if c.get("confidence_level") == leading_confidence
    ]

    if len(tied) < 2:
        return []

    missing_per_candidate = [
        set(c.get("missing_information", []))
        for c in tied
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

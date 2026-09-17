"""
Integration test — Phase 8 disambiguation loop (margin-based gate).

Verifies the structural contract of the new ambiguity detection path:

    round 1 → is_ambiguous() → get_discriminating_questions() → enrich_presentation()

Does NOT make a round-2 rag.run() call — that is stochastic and outside the
deterministic contract being tested here.

Run with pytest or directly:
    pytest tests/test_disambiguation_loop.py -v -s
    python tests/test_disambiguation_loop.py

Requires: live Cohere / Neo4j / Gemini credentials in .env (integration test).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "phase5"))
sys.path.insert(0, str(ROOT / "phase8"))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import rag
from disambiguate import (
    AMBIGUITY_MARGIN_THRESHOLD,
    is_ambiguous,
    get_discriminating_questions,
    enrich_presentation,
)

# Presentation chosen because it consistently produces a narrow top-2 margin
# (UTI vs AGE both retrieved; neither has confirmed discriminating features).
PRESENTATION = (
    "26F, 2 days fever, nausea, lower abdominal pain. Feeling weak. "
    "No urinary symptoms mentioned."
)


def test_disambiguation_loop():
    # ── Round 1 ───────────────────────────────────────────────────────────────
    result = rag.run(PRESENTATION)

    # 1. Score margin is attached to result by rag.run()
    assert "_score_margin" in result, (
        "_score_margin not attached to result — fused scoring not wired into run()"
    )
    margin = result["_score_margin"]
    candidates = result.get("candidates", [])
    top2_names = [c["diagnosis"] for c in candidates[:2]]
    print(f"\n  margin={margin:.4f}  threshold={AMBIGUITY_MARGIN_THRESHOLD}")
    print(f"  top-2 candidates: {top2_names}")

    # 2. Ambiguity gate fires on this presentation
    assert is_ambiguous(result), (
        f"Expected is_ambiguous=True for this presentation "
        f"(margin={margin:.4f}, threshold={AMBIGUITY_MARGIN_THRESHOLD}). "
        f"Top-2: {top2_names}"
    )

    # 3. Discriminating questions are produced
    questions = get_discriminating_questions(result)
    assert len(questions) > 0, (
        "get_discriminating_questions() returned empty list — "
        "top-2 candidates share all missing_information items or have none. "
        f"top-2 missing_information: "
        f"{[c.get('missing_information', []) for c in candidates[:2]]}"
    )
    print(f"  discriminating questions ({len(questions)}): {questions}")

    # 4. Every returned question is grounded in exactly one of the top-2 candidates.
    #    get_discriminating_questions() computes (mi_0 XOR mi_1) then deduplicates.
    #    So each question must appear in one missing_information set but not both.
    #    This verifies the structural invariant — not wording.
    mi_0 = set(candidates[0].get("missing_information", []))
    mi_1 = set(candidates[1].get("missing_information", []))
    symmetric_diff = (mi_0 - mi_1) | (mi_1 - mi_0)
    for q in questions:
        assert q in symmetric_diff, (
            f"Question '{q}' not in symmetric difference of top-2 missing_information — "
            f"it is either shared (non-discriminating) or invented.\n"
            f"  mi_0={mi_0}\n"
            f"  mi_1={mi_1}"
        )

    # 5. Enrichment appends the answer to the original presentation
    simulated_answer = "Patient reports burning on urination when asked directly."
    enriched = enrich_presentation(PRESENTATION, {questions[0]: simulated_answer})
    assert simulated_answer in enriched, (
        "Enrichment answer not present in enriched presentation"
    )
    assert PRESENTATION.rstrip(". ") in enriched, (
        "Original presentation not preserved in enriched presentation"
    )
    print(f"  enriched: ...{enriched[len(PRESENTATION):]}")


# ── Manual round-2 diagnostic (not part of the deterministic test contract) ──

if __name__ == "__main__":
    import json

    print("=" * 60)
    print("Round 1")
    print("=" * 60)
    result = rag.run(PRESENTATION)
    margin = result.get("_score_margin", None)
    print(f"leading: {result['leading_candidate']}")
    print(f"margin:  {margin}")
    print(f"ambiguous: {is_ambiguous(result)}")
    questions = get_discriminating_questions(result)
    print(f"questions: {questions}")

    if questions and is_ambiguous(result):
        simulated_answer = "Patient reports burning on urination when asked."
        enriched = enrich_presentation(PRESENTATION, {questions[0]: simulated_answer})
        print("\n" + "=" * 60)
        print("Round 2 (manual diagnostic — not a test assertion)")
        print("=" * 60)
        print(f"enriched presentation: {enriched}\n")
        result2 = rag.run(enriched)
        margin2 = result2.get("_score_margin", None)
        print(f"leading: {result2['leading_candidate']}")
        print(f"margin:  {margin2}")
        print(f"ambiguous: {is_ambiguous(result2)}")
        print(f"\nmargin delta: {margin:.4f} → {margin2:.4f}")
    else:
        print("\nSkipping round 2 — ambiguity gate did not fire or no questions.")

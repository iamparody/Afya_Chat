"""
Phase 8 reasoning evaluation harness.

Scores 9 dimensions per case using the rubric in rubric.py.

Dimensions:
    Deterministic (rubric.deterministic_scorers):
        leading_diagnosis, differential_relevance, confidence_range, red_flags
    LLM judge (rubric.judge_scorers):
        supporting_features, arguing_against_accuracy,
        missing_information_relevance, question_quality
    Special (requires initial + enriched):
        diagnostic_shift

Max score: 18 per case (9 dims x 2), 90 total (5 cases).

Usage:
    python phase8/evaluate_reasoning.py              # all 5 cases
    python phase8/evaluate_reasoning.py d1 d3        # specific cases
    python phase8/evaluate_reasoning.py --no-judge   # skip LLM judge (dry run)

Calibration note: run once with human review of judge scores before trusting
automated results in CI. The expected-answer set in rubric.py is the reference
standard — not the judge.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase5"))
sys.path.insert(0, str(ROOT / "phase8"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import rag
from disambiguate import is_ambiguous, get_discriminating_questions, enrich_presentation
from evaluate_disambiguation import CASES
from rubric import EXPECTED, deterministic_scorers, judge_scorers

PASS_SYM  = "✓"   # ✓
PART_SYM  = "△"   # △
FAIL_SYM  = "✗"   # ✗
SKIP_SYM  = "○"   # ○

# Ordered dimension list — drives scoring and reporting
DIMENSIONS = [
    ("leading_diagnosis",             "deterministic"),
    ("differential_relevance",        "deterministic"),
    ("confidence_range",              "deterministic"),
    ("red_flags",                     "deterministic"),
    ("supporting_features",           "judge"),
    ("arguing_against_accuracy",      "judge"),
    ("missing_information_relevance", "judge"),
    ("question_quality",              "judge"),
    ("diagnostic_shift",              "special"),
]

MAX_DIM_SCORE = 2
MAX_PER_CASE  = MAX_DIM_SCORE * len(DIMENSIONS)   # 18
MAX_TOTAL     = MAX_PER_CASE  * len(CASES)         # 90


# ── Special scorer ────────────────────────────────────────────────────────────

def score_diagnostic_shift(initial, enriched, expected):
    """
    Scores whether the enriched re-run shifts the leading candidate toward
    the expected diagnosis after clinician answers.

    Separate from other scorers because it requires both initial and enriched
    results rather than a single result dict.
    """
    if expected.get("is_negative_case"):
        return {"score": 2, "justification": "Negative case: no diagnostic shift expected or applicable."}

    if enriched is None:
        return {
            "score": 0,
            "justification": "No enriched result available (ambiguity did not fire or pipeline error).",
        }

    new_lead  = enriched.get("leading_candidate", "").lower()
    old_lead  = initial.get("leading_candidate", "")
    expected_leads = [e.lower() for e in expected.get("expected_enriched_leads", [])]

    if any(e in new_lead or new_lead in e for e in expected_leads):
        return {
            "score": 2,
            "justification": (
                f"Lead shifted to '{enriched.get('leading_candidate')}' — matches expected "
                f"{expected.get('expected_enriched_leads')}."
            ),
        }

    if old_lead.lower() != new_lead:
        return {
            "score": 1,
            "justification": (
                f"Lead shifted from '{old_lead}' to '{enriched.get('leading_candidate')}' "
                f"but not toward expected {expected.get('expected_enriched_leads')}."
            ),
        }

    return {
        "score": 0,
        "justification": (
            f"Lead did not shift after enrichment (still '{enriched.get('leading_candidate')}'); "
            f"expected one of {expected.get('expected_enriched_leads')}."
        ),
    }


# ── Case scorer ───────────────────────────────────────────────────────────────

def score_case(initial, enriched, expected, provider, use_judge):
    """
    Score all 9 dimensions for one case.
    Returns dict mapping dimension_name -> {"score": int, "justification": str}.
    score=-1 means dimension was skipped (--no-judge or not applicable).
    """
    scores = {}

    for dim, family in DIMENSIONS:
        if family == "deterministic":
            scores[dim] = deterministic_scorers[dim](initial, expected)

        elif family == "special":
            scores[dim] = score_diagnostic_shift(initial, enriched, expected)

        elif family == "judge":
            if not use_judge:
                scores[dim] = {"score": -1, "justification": "Skipped (--no-judge)"}
                continue
            scores[dim] = judge_scorers[dim](initial, expected, provider)

    return scores


# ── Reporter ──────────────────────────────────────────────────────────────────

def _sym(score):
    if score < 0:  return SKIP_SYM
    if score == 2: return PASS_SYM
    if score == 1: return PART_SYM
    return FAIL_SYM


def print_case_report(case_id, label, dim_scores, initial, questions):
    scored_dims = [v for v in dim_scores.values() if v["score"] >= 0]
    total = sum(v["score"] for v in scored_dims)
    max_p = len(scored_dims) * MAX_DIM_SCORE

    print(f"\n{'=' * 62}")
    print(f"Case {case_id}: {label}")
    print(f"Lead: {initial.get('leading_candidate', '?')}  |  Score: {total}/{max_p}")
    print(f"Questions: {questions if questions else '— none —'}")
    print(f"{'=' * 62}")

    for dim, _ in DIMENSIONS:
        r = dim_scores.get(dim, {"score": -1, "justification": "—"})
        s = r["score"]
        label_str = dim.replace("_", " ")
        score_str = f"{s}/2" if s >= 0 else "—"
        print(f"  {_sym(s)}  {label_str:<35} {score_str}")
        if r.get("justification") and r["justification"] not in ("—", ""):
            print(f"       {r['justification']}")

    return total, max_p


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all(case_ids=None, use_judge=True):
    cases_to_run = CASES
    if case_ids:
        cases_to_run = [c for c in CASES if c["id"] in case_ids]

    provider = None
    if use_judge:
        from providers import get_provider
        provider = get_provider()

    grand_total = 0
    grand_max   = 0
    all_results = []

    for case in cases_to_run:
        cid      = case["id"]
        expected = EXPECTED.get(cid)
        if not expected:
            print(f"\n{SKIP_SYM} Case {cid}: no EXPECTED entry — skipping")
            continue

        print(f"\nRunning {cid}: {case['label']} ...", flush=True)

        try:
            initial = rag.run(case["presentation"])
        except Exception as e:
            print(f"  {FAIL_SYM} PIPELINE ERROR (initial) — {e}")
            continue

        enriched  = None
        questions = []

        if not expected.get("is_negative_case"):
            questions = get_discriminating_questions(initial)

            if is_ambiguous(initial) and case.get("enrichment"):
                try:
                    ep = enrich_presentation(case["presentation"], case["enrichment"])
                    enriched = rag.run(ep)
                except Exception as e:
                    print(f"  {SKIP_SYM} PIPELINE ERROR (enriched) — {e}")

        dim_scores = score_case(initial, enriched, expected, provider, use_judge)

        case_total, case_max = print_case_report(
            cid, case["label"], dim_scores, initial, questions
        )
        grand_total += case_total
        grand_max   += case_max
        all_results.append({"id": cid, "total": case_total, "max": case_max, "scores": dim_scores})

    # ── Summary ───────────────────────────────────────────────────────────────
    pct = (100 * grand_total // grand_max) if grand_max else 0
    print(f"\n{'=' * 62}")
    print(f"BASELINE: {grand_total}/{grand_max} ({pct}%)")
    print(f"{'=' * 62}")
    print()
    print("Per-dimension summary:")
    for dim, _ in DIMENSIONS:
        dim_scores_all = [
            r["scores"][dim]["score"]
            for r in all_results
            if dim in r["scores"] and r["scores"][dim]["score"] >= 0
        ]
        if dim_scores_all:
            total_dim = sum(dim_scores_all)
            max_dim   = len(dim_scores_all) * MAX_DIM_SCORE
            print(f"  {dim.replace('_', ' '):<35} {total_dim}/{max_dim}")

    if use_judge:
        print()
        print(
            "Calibration: compare these scores against your own clinical judgement "
            "before treating the automated judge as ground truth. "
            "EXPECTED in rubric.py is the reference standard."
        )

    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 8 reasoning evaluation rubric")
    parser.add_argument("cases", nargs="*", help="Case IDs to run (e.g. d1 d3); omit for all")
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Skip LLM judge calls — scores deterministic dims only",
    )
    args = parser.parse_args()
    run_all(args.cases or None, use_judge=not args.no_judge)
